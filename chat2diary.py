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
            get_window_mode = "focused",  # 目前仅支持这一种
            window_classname = "Chrome_WidgetWin_1",
            window_title = "QQ",
            subwindow_classname = "Chrome_RenderWidgetHostHWND",
            subwindow_title = "Chrome Legacy Window",
            day_start_time_tag = "昨天",
            scrolldown = False,  # 向上滚动：程序自动将消息框从当前位置向上滚动到 day_start_time_tag 出现处的聊天消息；向下滚动：首先需要手动滚动到当天开始处的聊天记录，随后程序自动向下滚动窗口直到结束
            scrollsteps = 40,  # 每次程序滚动聊天窗口的距离
            singleshot = False,  # 只截取当前显示出来的一些聊天记录 (不滚动窗口)
            chatoutpath = "./chats-{Time}.txt",  # 将聊天记录保存到哪里；{Time} 标记将替换为当前时间戳
            diaryoutpath = "./diary-{Time}.txt",  # 将最后 AI 生成的日记文本保存到哪里；{Time} 标记将替换为当前时间戳
            appendoutput = False,  # 是否将聊天记录追加到 chatoutpath 文件中，而不是直接替换其中的文本
            msgtruncate = -1,  # 设置为正值 (非 0) 能够将每条消息超过特定长度的部分不给 LLM 看；适用于某些“小作文”长度的消息在全局中意义不大的情况，减少 LLM 推理负担
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
        self.get_window_mode = get_window_mode
        self.window_classname = window_classname
        self.window_title = window_title
        self.subwindow_classname = subwindow_classname
        self.subwindow_title = subwindow_title
        self.day_start_time_tag = day_start_time_tag
        self.scrolldown = scrolldown
        self.scrollsteps = scrollsteps
        self.singleshot = singleshot
        self.chatoutpath = chatoutpath
        self.diaryoutpath = diaryoutpath
        self.appendoutput = appendoutput
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


def insert_message_batch(message_batches: list, current_batch: list, config: Config, chat_extractor: ChatExtractor) -> bool:
    def finished_scrolling() -> bool:
        if config.singleshot:
            return True
        if config.scrolldown and (len(message_batches) > 1 and message_batches[-1] == message_batches[-2]):
            return True
        if not config.scrolldown and chat_extractor.check_reached_day_start(message_batches[0], config.day_start_time_tag):
            return True
        return False

    if config.scrolldown:
        message_batches.append(current_batch)
    else:
        message_batches.insert(0, current_batch)
    return not finished_scrolling()


def merge_lists(lists: list):
    result = []
    for l in lists:
        for elem in l:
            if elem not in result:
                result.append(elem)
    return result


def chat_to_diary(message_str: str, outpath: str, llm: LLM, config: Config, max_len_per_message = 2500):
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

    assert config.get_window_mode == "focused"

    print(f"Please click on your {config.window_title} ({config.window_classname}) window and leave your mouse and keyboard be.\nNow you have 3 sec. to do so\n3")
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(1)
    time.sleep(1)
    print("Starting.")

    # get all controls from currently focused window
    control = uiauto.GetFocusedControl()
    assert control
    controls_list: list[uiauto.Control] = []
    while control:  # recursively get parent controls
        controls_list.insert(0, control)
        control = control.GetParentControl()
    if len(controls_list) == 1:
        control = controls_list[0]
    else:
        control = controls_list[1]

    # find window (control) corresponding to config settings
    target_controls: list[uiauto.Control] = []
    for c in controls_list:
        if c.ClassName == config.window_classname or c.Name == config.window_title:
            target_controls.append(c)
        elif c.ClassName == config.subwindow_classname or c.Name == config.subwindow_title:
            target_controls.append(c)

    if config.verbose and config.debug:
        for c in target_controls:
            uiauto.LogControl(c)
            t = input(f"Show contens of {c.Name} ({c.ControlTypeName})? y/[n] ")
            t = str(t).lower()
            if t == 'y':
                uiauto.EnumAndLogControl(c)
            print()
    
    assert len(target_controls) > 0, f"Could not find window instance named {config.window_title} ({config.window_classname})"

    # find message list control
    msg_list_control = None
    for target in target_controls:
        msg_list_control = chat_extractor.find_message_list_panel(target)
        if msg_list_control is not None:
            break
    
    # simulate clicking on the message list panel, as to activate it and scroll it
    assert msg_list_control is not None, f"Could not locate a message list control named {chat_extractor.msg_list_control_name} ({chat_extractor.msg_list_control_typename}) in target window."
    # if config.debug:
    #     uiauto.EnumAndLogControl(msg_list_control)
    #     return
    message_batches = []
    chat_extractor.activate_message_list_panel(msg_list_control, wait=True)
    print("Please do not operate your computer, or the chat history browsing process would be interrupted...")
    while True:
        # grab all the messages and corresponding senders and other roles (in current msg panel)
        curr_messages = chat_extractor.extract_chat_context(msg_list_control)
        if not insert_message_batch(message_batches, curr_messages, config, chat_extractor):
            break
        # scroll up to get earlier messages
        chat_extractor.scroll_message_list_panel(msg_list_control, "down" if config.scrolldown else "up", config.scrollsteps)
    print(f"Finished browsing your {config.window_title} ({config.window_classname}) window, now you can freely operate your computer.")

    messages = merge_lists(message_batches)

    if config.verbose:
        print("Here are the messages got:")
        for msg in messages:
            print(msg)

    # save extracted chat history
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