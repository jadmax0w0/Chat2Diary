import time
import fire
import uiautomation as uiauto
from chatextract import *
from llmcalls import *
import os


class Config():
    def __init__(self):
        pass

    def init(
            self,
            fromfile = "",  # 直接读取之前程序提取出来并存储到文件中的聊天记录
            windowsearchmode = "traverse",  # focused: 程序启动时需要切换到目标程序的窗口; traverse: 程序启动时无需切换到目标程序的窗口
            windowsearchdepth = 3,  # 当 windowsearchmode 为 traverse 时，规定最深搜索几层窗口
            windowclassname = "Chrome_WidgetWin_1",
            windowname = "QQ",
            daystartlabel = "昨天",
            scrolldown = False,  # 向上滚动：程序自动将消息框从当前位置向上滚动到 daystartlabel 出现处的聊天消息；向下滚动：首先需要手动滚动到当天开始处的聊天记录，随后程序自动向下滚动窗口直到结束
            scrollsteps = 8,  # 每次程序滚动聊天窗口的距离
            singleshot = False,  # 只截取当前显示出来的一些聊天记录 (不滚动窗口)
            chatoutpath = "./chats-{Time}.txt",  # 将聊天记录保存到哪里；{Time} 标记将替换为当前时间戳
            diaryoutpath = "./diary-{Time}.txt",  # 将最后 AI 生成的日记文本保存到哪里；{Time} 标记将替换为当前时间戳
            appendoutput = False,  # 是否将聊天记录追加到 chatoutpath 文件中，而不是直接替换其中的文本
            chatbatchlen = 2500,  # 设置每次最多能够将多少字的聊天记录输入 LLM (同时也会保证输入的最后一条聊天记录是完整的)；如果聊天记录字数超过该 batch len，则会分多个批次将聊天记录依次输入 LLM，最终生成多段日记文本并拼合保存。设置为非正值则将全部聊天记录一次性导入 LLM。适用于避免聊天记录过长导致超出 LLM 上下文窗口限制。
            msgtruncate = 200,  # 设置为正值 (非 0) 能够将每条消息超过特定长度的部分不给 LLM 看，设置为非正值则把每条消息的所有内容输入 LLM。适用于某些“小作文”长度的消息在全局中意义不大的情况，减少 LLM 推理负担
            apikey: str = None,  # your api key here 调用 AI 模型的 api key
            modelid: str = None,  # your model id here 调用的 AI 模型 ID
            sysprompts = {
                "initial": "下面是一个有关长文本总结的问题。下面是一段聊天记录，其中每条消息的格式为“用户名 : 消息内容”，并且在消息之间会穿插有时间戳，标记着直到下一个时间戳出现期间每条消息发送的大致时间。请你将这段聊天记录总结为一篇详细的日记文本：",
                "continue": "下面是继续着之前内容的聊天记录，其中每条消息的格式仍为“用户名 : 消息内容”，并且在消息之间会穿插有时间戳，标记着直到下一个时间戳出现期间每条消息发送的大致时间。请你将这段聊天记录结合之前的日记总结，生成一段连贯的日记内容：",
                "final": "下面是最后一段聊天记录，其中每条消息的格式仍为“用户名 : 消息内容”，并且在消息之间会穿插有时间戳，标记着直到下一个时间戳出现期间每条消息发送的大致时间。请你将这段聊天记录结合之前的日记总结，生成一段连贯的日记内容：",
                "summary": "下面是一个有关长文本总结的问题。下面是一段日记文本，请你只用简短的一段话总结出其主要内容：",
            },  # 用于提示模型生成文本的提示词
            nosummary = False,  # 不保留每段日记的总结文本
            noai = False,  # 不使用 AI 生成日记文本，只提取聊天记录
            verbose = False,  # 显示更多输出
            debug = False,  # 调试模式 (可以调试自己的一些东西)
    ):
        self.fromfile = fromfile
        self.windowsearchmode = windowsearchmode
        self.windowsearchdepth = windowsearchdepth
        self.windowclassname = windowclassname
        self.windowname = windowname
        self.daystartlabel = daystartlabel
        self.scrolldown = scrolldown
        self.scrollsteps = scrollsteps
        self.singleshot = singleshot
        self.chatoutpath = chatoutpath
        self.diaryoutpath = diaryoutpath
        self.appendoutput = appendoutput
        self.chatbatchlen = chatbatchlen
        self.msgtruncate = msgtruncate
        self.apikey = apikey
        self.modelid = modelid
        self.sysprompts = sysprompts
        self.nosummary = nosummary
        self.noai = noai
        self.verbose = verbose
        self.debug = debug

        self.curr_msg_role_control_info_id = 0

        return True

    def murmur(self, *args, end: str = "\n"):
        if self.verbose:
            print(*args, end=end)

    def next_msg_control_info(self):
        i = self.curr_msg_role_control_info_id
        info = (self.msg_roles_control_typenames[i], self.msg_roles_control_localdepth[i])
        self.curr_msg_role_control_info_id = (self.curr_msg_role_control_info_id + 1) % self.msg_roles_num
        return info
    
    def format_output_path(self):
        curr_time = time.localtime()
        time_str = f"{'{:02d}'.format(curr_time.tm_year)}{'{:02d}'.format(curr_time.tm_mon)}{'{:02d}'.format(curr_time.tm_mday)}{'{:02d}'.format(curr_time.tm_hour)}{'{:02d}'.format(curr_time.tm_min)}{'{:02d}'.format(curr_time.tm_sec)}"
        return self.chatoutpath.replace("{Time}", time_str), self.diaryoutpath.replace("{Time}", time_str)


def get_target_control(config: Config) -> uiauto.Control:
    if config.windowsearchmode.lower() == "focused":
        print(f"Please click on your {config.windowname} ({config.windowclassname}) window and leave your mouse and keyboard be.\nNow you have 3 sec. to do so\n3")
        time.sleep(1)
        print(2)
        time.sleep(1)
        print(1)
        time.sleep(1)
        print("Started.")

        # get all parent controls from currently focused control, since currently focused control might be a child of target window
        control = uiauto.GetFocusedControl()
        while control:  # recursively get parent controls
            if control.Name == config.windowname and control.ClassName == config.windowclassname:
                print("Confirmed that currently window is target window.")
                return control
            control = control.GetParentControl()
        print(f"Currently focused window is not a window of {config.windowname} ({config.windowclassname}).")
    else:
        print("Locating core window... ", end="")
        control = uiauto.GetFocusedControl()
        while control.GetParentControl():
            control = control.GetParentControl()
        print(f"Loaded: {control.Name} ({control.ControlTypeName})")
        for i in range(config.windowsearchdepth):
            print(f"Searching target window {config.windowname} ({config.windowclassname}) with max depth of {i+1}... ", end="")
            for c, _ in uiauto.WalkControl(control, maxDepth=i+1):
                if c.Name == config.windowname and c.ClassName == config.windowclassname:
                    print("Found.")
                    return c
            print("Failed.")
    return None


def insert_message_batch(message_batches: list, current_batch: list, config: Config, chat_extractor: ChatExtractor) -> bool:
    def finished_scrolling() -> bool:
        if config.singleshot:
            return True
        if config.scrolldown and (len(message_batches) > 1 and message_batches[-1] == message_batches[-2]):
            return True
        if not config.scrolldown and chat_extractor.check_reached_day_start(message_batches[0], config.daystartlabel):
            return True
        return False

    if config.scrolldown:
        message_batches.append(current_batch)
    else:
        message_batches.insert(0, current_batch)
    return not finished_scrolling()


def merge_lists(lists: list[list]):
    if not lists or len(lists) <= 0:
        return []
    for l in lists:
        if not isinstance(l, list):
            print(f"Warning: messages extracted by {ChatExtractor.__name__}.{ChatExtractor.extract_chat_context.__name__}() are not lists, please make sure this matches your expectation. Now skipping merging them...")
            return lists

    result = []
    for l in lists:
        for elem in l:
            if elem not in result:
                result.append(elem)
    return result


def chat_to_diary(message_str: str, outpath: str, llm: LLM, config: Config):
    max_len_per_message = config.chatbatchlen

    day_of_week = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    curr_time = time.localtime()
    out_diary = f"日记 - {'{:02d}'.format(curr_time.tm_year)} 年 {'{:02d}'.format(curr_time.tm_mon)} 月 {'{:02d}'.format(curr_time.tm_mday)} 日 {day_of_week[curr_time.tm_wday]} ({'{:02d}'.format(curr_time.tm_hour)}:{'{:02d}'.format(curr_time.tm_min)})"

    llm.llm_init(apikey=config.apikey, modelid=config.modelid)
    message_str_len = len(message_str)
    msg_slice_start, msg_slice_end = 0, min(max_len_per_message, message_str_len)
    while msg_slice_start < message_str_len:
        while message_str[msg_slice_end - 1] != '\n' and msg_slice_end < message_str_len:
            msg_slice_end += 1
        message_slice = message_str[msg_slice_start:msg_slice_end]
        # call ai
        response = ""
        prev_summary = ""
        if msg_slice_start == 0:
            response = llm.llm_prompt(message_slice, config.sysprompts['initial'], streaming=False)
            prev_summary = llm.llm_prompt(response, config.sysprompts['summary'], streaming=False)
        # elif msg_slice_end < message_str_len:
        else:
            response = llm.llm_prompt(f"上一段日记总结：\n{prev_summary}\n\n接下来的聊天记录：\n{message_slice}", config.sysprompts['continue'], streaming=False)
            prev_summary = llm.llm_prompt(response, config.sysprompts['summary'], streaming=False)
        # else:
        #     response = doubao.doubao_prompt(f"上一段日记总结：\n{prev_summary}\n\n最后一段聊天记录：\n{message_slice}", config.sysprompts['final'], streaming=False)
        #     prev_summary = doubao.doubao_prompt(response, config.sysprompts['summary'], streaming=False)
        config.murmur(response, end="\n---SUM---\n")
        config.murmur(prev_summary, end="\n---------\n")
        out_diary += "\n\n---------\n\n" + response + (f"\n\n(总结：{prev_summary})" if not config.nosummary else "")
        msg_slice_start = msg_slice_end
        msg_slice_end = min(msg_slice_start + max_len_per_message, message_str_len)
    with open(outpath, 'wb') as f:
        f.write(out_diary.encode('utf-8'))
    llm.llm_close()


def main(config: Config, chat_extractor: ChatExtractor, llm: LLM):
    if os.path.isfile(config.fromfile):
        if config.noai:
            print("Why?")
            return
        print("Calling LLM to get a diary...")
        diary_outpath = config.format_output_path()[1]
        with open(config.fromfile, 'rb') as f:
            content = f.read().decode('utf-8')
            chat_to_diary(content, diary_outpath, llm, config)
        print(f"Diary saved to file {diary_outpath}")
        return

    # find target window
    config.murmur(f"Window search mode: {config.windowsearchmode}")
    target_control = get_target_control(config)
    if config.verbose and config.debug:
        uiauto.LogControl(target_control)
        t = input(f"Show contens of {target_control.Name} ({target_control.ControlTypeName})? y/[n] ").lower()
        if t == 'y':
            uiauto.EnumAndLogControl(target_control)
        print()
    
    assert target_control is not None, f"Could not find window instance named {config.windowname} ({config.windowclassname})"

    # find message list control
    msg_list_control = chat_extractor.find_message_list_panel(target_control)
    
    # activate the message list panel and simulate scrolling it
    assert msg_list_control is not None, f"Could not locate a message list control named {chat_extractor.msg_list_control_name} ({chat_extractor.msg_list_control_typename}) in target window."
    if config.verbose and config.debug:
        t = input(f"Show contens of {msg_list_control.Name} ({msg_list_control.ControlTypeName})? y/[n] ").lower()
        if t == 'y':
            uiauto.EnumAndLogControl(msg_list_control)
        print()
    message_batches = []
    chat_extractor.activate_message_list_panel(msg_list_control)
    print("Please do not operate your computer, or the chat history browsing process would be interrupted...")
    while True:
        # grab all the messages and corresponding senders and other roles (in current msg panel)
        # chat_extractor.activate_message_list_panel(msg_list_control)
        curr_messages = chat_extractor.extract_chat_context(msg_list_control)
        if not insert_message_batch(message_batches, curr_messages, config, chat_extractor):
            break
        # scroll up to get earlier messages
        chat_extractor.scroll_message_list_panel(msg_list_control, "down" if config.scrolldown else "up", config.scrollsteps)
    print(f"Finished browsing your {config.windowname} ({config.windowclassname}) window, now you can freely operate your computer.")

    messages = merge_lists(message_batches)

    if config.verbose:
        print("Here are the messages got:")
        for msg in messages:
            print(msg)

    # save extracted chat history
    if config.debug:
        if input("Continue to save chat history? y/[n]").lower() != 'y':
            return
    message_str = chat_extractor.chat_context_to_str(messages)
    chat_outpath = config.format_output_path()[0]
    if config.appendoutput:
        with open(chat_outpath, mode="ab") as f:
            f.write(f"\n{message_str}".encode('utf-8'))
    else:
        with open(chat_outpath, mode="wb") as f:
            f.write(message_str.encode('utf-8'))
    print(f"Chat history saved to file {chat_outpath}")

    # start prompting ai to generate a diary text
    if not config.noai:
        if config.debug:
            if input("Continue to call LLM? y/[n]").lower() != 'y':
                return
        print("Calling LLM to get a diary...")
        message_str = chat_extractor.chat_context_to_str(messages, per_msg_truncate=config.msgtruncate)
        config.murmur("------------\nChat context sent to LLM: ")
        config.murmur(message_str)
        config.murmur("------------")
        if config.debug:
            t = input("Is this chat context available? [y]/n").lower()
            if t == 'n':
                return
        diary_outpath = config.format_output_path()[1]
        chat_to_diary(message_str, diary_outpath, llm, config)
        print(f"Diary saved to file {diary_outpath}")


if __name__ == "__main__":
    config = Config()
    initiated = fire.Fire(config.init)
    if initiated:
        main(config, QQChatExtractor(), DoubaoLLM())