import uiautomation as uiauto
import time


class ChatExtractor():
    def __init__(self):
        self.msg_list_control_typename: str = None
        self.msg_list_control_name: str = None
        self.msgbox_control_localdepth: int = -1
        self.day_start_tag_content: str = None
        raise NotImplementedError()
    
    def find_message_list_panel(self, parent: uiauto.Control) -> uiauto.Control:
        raise NotImplementedError()
    
    def activate_message_list_panel(self, panel: uiauto.Control, wait = True):
        print(f"Activating {panel.Name} ({panel.ControlTypeName}), please wait... ", end='')
        panel.Click()
        if wait:
            time.sleep(1)
        print(f"Activated.")

    def scroll_message_list_panel(self, panel: uiauto.Control, direction: str = "down", scroll_times: int = 20):
        direction = direction.lower()
        if direction == 'up':
            direction = "{Up}"
        elif direction == 'down':
            direction = "{Down}"
        elif direction == 'left':
            direction = "{Left}"
        elif direction == 'right':
            direction = "{Right}"
        else:
            direction = "{Down}"

        scroll_cmds = [direction for _ in range(scroll_times)]
        scroll_cmds = "".join(scroll_cmds)
        # self.activate_message_list_panel(panel, wait=False)
        uiauto.SendKeys(scroll_cmds)

    def check_reached_day_start(self, msg) -> bool:
        raise NotImplementedError()

    def try_form_message(self, control: uiauto.Control, local_depth: int) -> tuple:
        raise NotImplementedError()
    
    def extract_chat_context(self, parent: uiauto.Control):
        raise NotImplementedError()
    
    def chat_context_to_str(self, chat_context, **kwargs):
        raise NotImplementedError()
    

class QQChatExtractor(ChatExtractor):
    def __init__(self):
        # try:
        #     super().__init__()
        # except NotImplementedError:
        #     pass
        # except Exception as e:
        #     print(f"An error has occured: ({type(e)}) {e}")
        self.msg_list_control_typename: str = "WindowControl"
        self.msg_list_control_name: str = "消息列表"
        self.msgbox_control_localdepth = 5
        # self.sender_control_typename: str = "GroupControl"
        # self.sender_control_localdepth: int = int(6)
        # self.content_control_typename: str = "TextControl"
        # self.content_control_localdepth: int = int(8)
        # self.time_tag_control_typename = "TextControl"
        # self.time_tag_control_localdepth = 6
        # self.day_start_tag_content = "昨天"

        self.timestamp_hint = "<时间戳>"
        self.withdrawn_chat_hint = "<撤回消息>"

    def find_message_list_panel(self, parent):
        msg_list_control: uiauto.Control = None
        for c, _ in uiauto.WalkControl(parent):
            # print(f"{c.ControlTypeName} | {c.Name} [{self.msg_list_control_typename} | {self.msg_list_control_name}]")
            if c.ControlTypeName == self.msg_list_control_typename and c.Name == self.msg_list_control_name:
                msg_list_control = c
                break
        # assert msg_list_control is not None, f"Could not find a message list control named {self.msg_list_control_name} ({self.msg_list_control_typename})"
        return msg_list_control
    
    def check_reached_day_start(self, message_batch: list, day_start_tag: str = "昨天"):
        day_start = False
        for msg in message_batch:
            # if role == self.timestamp_hint and self.day_start_tag_content in content:
            role = msg[0]
            if day_start_tag in role:
                day_start = True
                break
        return day_start
    
    def try_form_message(self, control, local_depth) -> tuple[str, str]:
        if local_depth != self.msgbox_control_localdepth:
            return None
        # 遇到了一条消息
        sender = ""
        content = ""
        for c, d in uiauto.WalkControl(control):
            if d == 1:
                sender += f" {c.Name}"
            else:
                content += c.Name
        return (sender, content)
        # if control.ControlTypeName == self.time_tag_control_typename and local_depth == self.time_tag_control_localdepth:  # qq 中的时间标记
        #     return 'timestamp'
        # if control.ControlTypeName == self.content_control_typename and local_depth == self.sender_control_localdepth + 1:
        #     return 'withdrawn'
        # if control.ControlTypeName == self.sender_control_typename and local_depth == self.sender_control_localdepth:  # qq 中的发送者标记
        #     return 'sender'
        # if control.ControlTypeName == self.content_control_typename and local_depth == self.content_control_localdepth:  # qq 中的普通发送内容
        #     return 'content'
        # if control.ControlTypeName == "GroupControl" and local_depth == self.content_control_localdepth:  # and control.Name == '表情':  # 发送内容可能是个表情包
        #     return 'content'
        # if control.ControlTypeName == "ImageControl" and local_depth == self.content_control_localdepth:  # 发送内容是个图片
        #     return 'content'
        # return None

    def extract_chat_context(self, parent):
        """
        导出的内容格式：[(发送人, 内容, [重复内容标记]), ...]
        """
        contexts = []
        # curr_message_role = "sender"
        # message_senders = []
        # message_contents = []
        for c, d in uiauto.WalkControl(parent):
            msg = self.try_form_message(c, d)
            if msg is None:
                continue
            sender, content = msg
            repeat_id = 0
            while (sender, content, repeat_id) in contexts:
                repeat_id += 1
            contexts.append((sender, content, repeat_id))
            # if msg_role == 'sender':
            # if curr_message_role == 'sender' and msg_role == 'timestamp':
            #     message_senders.append(self.timestamp_hint)
            #     message_contents.append(c.Name)
            # elif curr_message_role == 'sender' and msg_role == 'withdrawn':
            #     message_senders.append(self.withdrawn_chat_hint)
            #     message_contents.append(c.Name)
            # elif curr_message_role == "sender" and msg_role == 'sender':
            #     message_senders.append(c.Name)
            #     curr_message_role = "content"
            # elif curr_message_role == "content" and msg_role == 'content':
            #     message_contents.append(c.Name)
            #     curr_message_role = "sender"
                
        # if len(message_senders) != len(message_contents):
        #     print(f"Warning: number of message senders ({len(message_senders)}) does not equal to number of message contents ({len(message_contents)}).")

        # for i in range(min(len(message_senders), len(message_contents))):
        #     contents.append((message_senders[i], message_contents[i]))
        return contexts
    
    def chat_context_to_str(self, chat_context: list[tuple[str, str, int]], **kwargs):
        per_msg_truncate = -1
        if "per_msg_truncate" in kwargs:
            per_msg_truncate = int(kwargs["per_msg_truncate"])

        message_str = ""
        for msg in chat_context:
            sender, content = (msg[0] if msg[0] is not None else ""), (msg[1] if msg[1] is not None else "")
            if per_msg_truncate > 0:
                sender = sender[:min(len(sender), per_msg_truncate)]
                content = content[:min(len(content), per_msg_truncate)]
            if sender.replace(' ', '') == "":
                message_str += content
            elif content == "":
                message_str += sender
            else:
                message_str += f"{sender}: {content}"
            message_str += '\n'
        
        return message_str