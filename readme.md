# Chat2Diary

将新版 QQ 中的聊天记录导出，并使用大模型生成一段 (或多段) 日记文本。

## 功能扩展

- 大模型现在实现了调用豆包大模型的方法。如果需要调用其他的大模型，则可以自行在 `llmcalls.py` 中派生 `LLM` 类并实现其中方法。
- 如果需要实现导出微信或者老版 QQ 聊天记录，则可以自行在 `chatextract.py` 中派生 `ChatExtractor` 类并实现其中方法：
  - `find_message_list_panel` 方法接受的是一个 Control，并从中寻找包含消息列表的组件 Control，随后返回；
  - `check_reached_day_start` 方法接受一组提取出来的消息记录，并判断是否到达了“今天”的开始位置；
  - `try_form_message` 方法接受一个 Control，并尝试从该 Control 及其所含的子 Control 中提取出来一条聊天消息；
  - `extract_chat_context` 方法接受消息列表组件的 Control，并将其目前所含有的消息记录提取出来；推荐将每一条消息作为一个对象，并将所有消息整合为一个 `list` 后返回。可以结合 `try_form_message` 使用；
  - `chat_context_to_str` 方法接受提取出来的消息记录 (`list` 类型；每个元素是每次调用 `extract_chat_context` 的返回内容) 并将其合并为字符串。

## 使用方法

可以直接调用 `./dist/` 下的 `chat2diary.exe`，也可以自行通过 `requirements.txt` 安装所需环境后，调用 `python ./chat2diary.py [flags]`。

### Flags 说明

每个标志的详细作用详见 `chat2diary.py`。

### 用例

如果你想只导出窗口当前显示的消息记录并生成日记文本，那么可以调用：

```bash
python ./chat2diary.py --singleshot --apikey="your api key here" --modelid="your model id here"
```

如果你想从聊天界面的最底端开始向上滚动导出聊天记录 (程序将会自动将窗口向上滚动，直到这一天的开始位置。开始位置的标志文本可以由 `--day_start_time-tag` 设置)，那么可以调用：

```bash
python ./chat2diary.py --apikey="your api key here" --modelid="your model id here"
```

如果你想从聊天界面的某处开始向下滚动导出聊天记录 (程序将会自动将窗口向下滚动，直到程序发现某两次滚动提取出来的消息记录一致，比如滚动到了窗口最下端)，那么可以调用：

```bash
python ./chat2diary.py --scrolldown --apikey="your api key here" --modelid="your model id here"
```

如果你只想导出聊天记录而不生成日记文本，那么可以调用：

```bash
python ./chat2diary.py --noai
```

随后可以按需添加 `--scrolldown`, `--singleshot` 等标志。

### 注意

- 按下回车开始执行命令后，程序会留给你 3 秒的时间切换到 QQ 窗口。切换到 QQ 窗口后会看到鼠标自动移动向消息界面的中间位置处并模拟鼠标点击；此时如果发现鼠标点击到了一个消息气泡 (该气泡会被激活而变暗)，那么请迅速点击一下气泡周围的空白位置，取消激活该气泡；或者切换回命令行，按下 `Ctrl+C` 结束程序，随后将 QQ 的消息界面滚动一下，避免鼠标点击到消息气泡即可。

    > [!question] 为什么要这么做呢？
    >
    > 因为程序是模拟点击键盘上的上下箭头键来滚动消息界面。如果 QQ 中目前点击激活了一个消息气泡，那么上下箭头键会作用到消息气泡上，造成的现象就是消息界面会乱跳一通。如果没能及时反应过来取消激活聊天气泡，当发现消息界面在乱跳时，同样可以及时切换回命令行并结束程序，随后调整聊天界面位置。
    >
    > 以后我会试着将上下箭头键改为模拟鼠标滚轮。

- 发现程序自动移动鼠标并开始滚动消息界面后，就不要再操作电脑了，直到程序在命令行中输出“... now you can freely operate your computer.”一行消息，此时才可以操作电脑。
