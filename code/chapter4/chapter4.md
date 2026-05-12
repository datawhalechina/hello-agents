### 1. llm_client文件的作用：

定义了一个HelloAgentsLLM的类，首先完成apikey的初始化，后面定义了一个**think函数（messages）：这个函数能够进行流式输出，并返回输出的所有内容。**（有副作用，产生的直接输出到控制台）I/O流输出。

后面用responseText接收了return的值，在最后再打印完整内容。这个think函数就输出：流式输出和打印空格。

### 2.Plan_and_solve文件的作用：

定义了一个Planner类，完成llm_client的初始化，后面定义了一个**plan函数（问题）：这个函数能够把plan分成列表返回**

定义了一个Executor类，完成llm_client的初始化，后面定义了一个**execute函数（问题，计划）：这个函数针对每个plan里面的具体步骤进行回答产生一个response_text。会打印每个问题及其回答，最后返回最后的答案final_answer。**

定义了一个PlanAndSolveAgent类，**这是一个整合的类**。完成llm_client的初始化，后面定义了一个**run函数（问题）：把问题输入产生plan，然后把question和plan输入产生final_answer，最后输出final_answer。**

### 3.ReAct文件的作用：

定义了一个**ReActAgent类，有一个run函数（问题），会输出第几步---输出thought--输出action：【工具名】要搜索的内容---输出observation：搜到的答案--print("已达到最大步数，流程终止。")**

还有一个**_parse_output函数（文本），作用是提取文本里面的thought和action。**

还有一个_parse_action函数（action_text），**作用是获得action_text里面的工具名和问题输入，例如：输入 "Search[华为最新手机]" → match 成功，返回 ("Search", "华为最新手机")**

还有一个**_parse_action_input函数（action_text），作用是获得action_text里面的问题输入。例如输入 "Search[华为最新手机]" → 返回 "华为最新手机**

### 4.Reflection文件的作用：

定义了一个Memory类，有一个**add_record函数（记录类型，记录的具体内容），作用是向记录里面新增一条记录类型**

还有一个**函数get_trajectory，作用是将所有记忆记录格式化为一个连贯的字符串文本，用于构建提示词。**

还有一个**函数get_last_execution，作用是获得最后一次执行的内容。**

定义了一个类ReflectionAgent，有一个**run函数（task），作用是处理任务，进行初试执行，反思和再次审核。最后返回最后生成的代码。（迭代是反思与优化）**

还有一个**函数_get_llm_response（prompt），作用是生成prompt的答案**

### 5.tools文件的作用：（工具函数得自己写，然后把工具函数注册成工具）

定义了一个**search函数（疑问），返回一个最好的答案。**

定义了一个ToolExecutor类，里面有一个**registerTool函数（名字，描述，调用函数），作用是注册工具。**

还有一个**getTool函数（名字），作用是从字典中取出名为 name 的工具，并返回该工具对应的执行函数。例如search**

还有一个是**getAvailableTools函数，作用是获得所有工具的描述字符串。**
