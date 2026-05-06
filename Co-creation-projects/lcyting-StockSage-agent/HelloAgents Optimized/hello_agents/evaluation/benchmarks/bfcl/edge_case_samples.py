"""
BFCL 四类别的边界测试样本设计

每个类别 3 个测试样本，聚焦边界情况和易错场景。

设计思路：
- simple: 参数类型混淆、缺失必需参数、嵌套结构
- multiple: 顺序依赖、循环调用、部分失败恢复
- parallel: 共享副作用、竞态条件、重复去重
- irrelevance: 隐式调用、条件触发、自定义行为
"""

SIMPLE_EDGE_CASES = [
    {
        "id": "simple_edge_1",
        "question": "The price of an item is $1,234.56. Apply a 15% discount and then add 8.5% sales tax. What is the final price? Round to 2 decimal places.",
        "function": [
            {
                "name": "apply_discount",
                "description": "Apply a percentage discount to a price",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number", "description": "Original price"},
                        "discount_percent": {
                            "type": "number",
                            "description": "Discount percentage",
                        },
                    },
                    "required": ["price", "discount_percent"],
                },
            },
            {
                "name": "apply_tax",
                "description": "Add sales tax to a price",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number", "description": "Price before tax"},
                        "tax_percent": {
                            "type": "number",
                            "description": "Tax percentage",
                        },
                    },
                    "required": ["price", "tax_percent"],
                },
            },
            {
                "name": "round_price",
                "description": "Round price to specified decimal places",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number", "description": "Price to round"},
                        "decimals": {
                            "type": "integer",
                            "description": "Number of decimal places",
                        },
                    },
                    "required": ["price", "decimals"],
                },
            },
        ],
        "ground_truth": [
            {"apply_discount": {"price": [1234.56], "discount_percent": [15]}},
            {"apply_tax": {"price": [1049.376], "tax_percent": [8.5]}},
            {"round_price": {"price": [1138.57296], "decimals": [2]}},
        ],
        "_note": "Fraught: user said '$1,234.56', model may pass string '$1,234.56' instead of float 1234.56. Also model may try to do all math inline instead of calling functions.",
    },
    {
        "id": "simple_edge_2",
        "question": "Find books by 'Haruki Murakami' published after 2000, but exclude 'Norwegian Wood'. Sort by rating descending.",
        "function": [
            {
                "name": "search_books",
                "description": "Search books by author",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "author": {"type": "string", "description": "Author name"},
                        "after_year": {
                            "type": "integer",
                            "description": "Published after this year (optional)",
                        },
                    },
                    "required": ["author"],
                },
            },
            {
                "name": "filter_books",
                "description": "Filter books by title exclusion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exclude_titles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Titles to exclude",
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["rating", "title", "year"],
                            "description": "Sort field",
                        },
                    },
                    "required": ["exclude_titles", "sort_by"],
                },
            },
        ],
        "ground_truth": [
            {"search_books": {"author": ["Haruki Murakami"], "after_year": [2000]}},
            {
                "filter_books": {
                    "exclude_titles": [["Norwegian Wood"]],
                    "sort_by": ["rating"],
                }
            },
        ],
        "_note": "'after_year' is optional but required for correctness. Model may skip it. 'exclude_titles' expects an array — model may pass a single string.",
    },
    {
        "id": "simple_edge_3",
        "question": "Create a new user with the following nested profile: name='Alice', address={'city': 'Paris', 'zip': 75001}, tags=['vip', 'premium'].",
        "function": [
            {
                "name": "create_user",
                "description": "Create a new user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "User name"},
                        "profile": {
                            "type": "object",
                            "description": "User profile with nested fields",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "User tags",
                        },
                    },
                    "required": ["name", "profile", "tags"],
                },
            }
        ],
        "ground_truth": [
            {
                "create_user": {
                    "name": ["Alice"],
                    "profile": [{"city": "Paris", "zip": 75001}],
                    "tags": [["vip", "premium"]],
                }
            }
        ],
        "_note": "Nested dict and array in args. Model may flatten the nested structure or pass wrong types.",
    },
]


MULTIPLE_EDGE_CASES = [
    {
        "id": "multiple_edge_1",
        "question": "First, calculate 2^10. Then take that result and pass it to is_prime to check if it's prime. If it's not prime, call factorize on it.",
        "function": [
            {
                "name": "power",
                "description": "Calculate base raised to exponent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base": {"type": "integer"},
                        "exp": {"type": "integer"},
                    },
                    "required": ["base", "exp"],
                },
            },
            {
                "name": "is_prime",
                "description": "Check if a number is prime",
                "parameters": {
                    "type": "object",
                    "properties": {"n": {"type": "integer"}},
                    "required": ["n"],
                },
            },
            {
                "name": "factorize",
                "description": "Factorize a number into prime factors",
                "parameters": {
                    "type": "object",
                    "properties": {"n": {"type": "integer"}},
                    "required": ["n"],
                },
            },
        ],
        "ground_truth": [
            {"power": {"base": [2], "exp": [10]}},
            {"is_prime": {"n": [1024]}},
            {"factorize": {"n": [1024]}},
        ],
        "_note": "Three calls with data dependency: output of step 1 feeds step 2, output of step 2 determines if step 3 is needed. Model may try to compute 2^10 inline instead of calling power().",
    },
    {
        "id": "multiple_edge_2",
        "question": "Send an email to alice@example.com and also send an email to bob@example.com. Wait — actually, use send_bulk_email instead if available. If not, send two separate emails.",
        "function": [
            {
                "name": "send_email",
                "description": "Send a single email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "subject": {"type": "string"},
                    },
                    "required": ["to", "subject"],
                },
            },
            {
                "name": "send_bulk_email",
                "description": "Send email to multiple recipients",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipients": {"type": "array", "items": {"type": "string"}},
                        "subject": {"type": "string"},
                    },
                    "required": ["recipients", "subject"],
                },
            },
        ],
        "ground_truth": [
            {"send_email": {"to": ["alice@example.com"], "subject": ["No subject"]}},
            {"send_email": {"to": ["bob@example.com"], "subject": ["No subject"]}},
        ],
        "_note": "Ambiguous instruction. The model may choose send_bulk_email or send_email x2. Both should be acceptable if both are in the function list. Tests the model's ability to handle instruction ambiguity.",
    },
    {
        "id": "multiple_edge_3",
        "question": "Get the weather for Tokyo, then get the weather for London, then get the weather for Tokyo again. Cache should handle the repeat.",
        "function": [
            {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ],
        "ground_truth": [
            {"get_weather": {"city": ["Tokyo"]}},
            {"get_weather": {"city": ["London"]}},
            {"get_weather": {"city": ["Tokyo"]}},
        ],
        "_note": "Three calls with a repeat. Model may deduplicate and only output two calls (Tokyo, London), losing the third. Tests whether the model preserves exact call count.",
    },
]


PARALLEL_EDGE_CASES = [
    {
        "id": "parallel_edge_1",
        "question": "For the following cities, get the weather and the local time simultaneously: ('New York', 'Tokyo', 'London'). Return results as a combined report.",
        "function": [
            {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
            {
                "name": "get_local_time",
                "description": "Get local time for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        ],
        "ground_truth": [
            {"get_weather": {"city": ["New York"]}},
            {"get_local_time": {"city": ["New York"]}},
            {"get_weather": {"city": ["Tokyo"]}},
            {"get_local_time": {"city": ["Tokyo"]}},
            {"get_weather": {"city": ["London"]}},
            {"get_local_time": {"city": ["London"]}},
        ],
        "_note": "6 parallel calls: 2 functions x 3 cities. Model may batch by function (3 weather calls then 3 time calls) or by city (weather+time per city). Both valid strategies as long as all 6 calls are present.",
    },
    {
        "id": "parallel_edge_2",
        "question": "Book a flight from NYC to London for 5 people on the same flight. Each passenger must be added to the booking.",
        "function": [
            {
                "name": "search_flight",
                "description": "Search for available flights",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "destination": {"type": "string"},
                    },
                    "required": ["origin", "destination"],
                },
            },
            {
                "name": "book_seat",
                "description": "Book a seat for a passenger on a flight",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "flight_id": {"type": "string"},
                        "passenger_name": {"type": "string"},
                        "seat_preference": {
                            "type": "string",
                            "enum": ["window", "aisle", "middle"],
                        },
                    },
                    "required": ["flight_id", "passenger_name"],
                },
            },
        ],
        "ground_truth": [
            {"search_flight": {"origin": ["NYC"], "destination": ["London"]}},
            {"book_seat": {"flight_id": [""], "passenger_name": ["Passenger 1"]}},
            {"book_seat": {"flight_id": [""], "passenger_name": ["Passenger 2"]}},
            {"book_seat": {"flight_id": [""], "passenger_name": ["Passenger 3"]}},
            {"book_seat": {"flight_id": [""], "passenger_name": ["Passenger 4"]}},
            {"book_seat": {"flight_id": [""], "passenger_name": ["Passenger 5"]}},
        ],
        "_note": "search_flight must come first (data dependency), then 5 book_seat calls can be parallel. Model may try to book all 5 in one call with a 'passengers' list. Tests handling of serial-then-parallel patterns.",
    },
    {
        "id": "parallel_edge_3",
        "question": "Increment the global counter 3 times.",
        "function": [
            {
                "name": "increment_counter",
                "description": "Increment a global counter by 1",
                "parameters": {"type": "object", "properties": {}},
                "required": [],
            }
        ],
        "ground_truth": [
            {"increment_counter": {}},
            {"increment_counter": {}},
            {"increment_counter": {}},
        ],
        "_note": "3 identical calls with no args. Model may deduplicate to one call and pass 'count=3' even though no such param exists. Tests ability to call the same function multiple times with no arguments.",
    },
]


IRRELEVANCE_EDGE_CASES = [
    {
        "id": "irrelevance_edge_1",
        "question": "What is the capital of France?",
        "function": [
            {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
            {
                "name": "calculate",
                "description": "Perform a calculation",
                "parameters": {
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                    "required": ["expression"],
                },
            },
        ],
        "ground_truth": [],
        "_note": "Pure knowledge question, no tool needed. Model should NOT call any function. Tests resistance to unnecessary tool invocation.",
    },
    {
        "id": "irrelevance_edge_2",
        "question": "Tell me a joke.",
        "function": [
            {
                "name": "search_web",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        ],
        "ground_truth": [],
        "_note": "Model may 'over-assist' by searching for a joke online instead of generating one. Tests reluctance to call tools when not needed.",
    },
    {
        "id": "irrelevance_edge_3",
        "question": "What is the square root of -1?",
        "function": [
            {
                "name": "python_repl",
                "description": "Execute Python code and return the result",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            }
        ],
        "ground_truth": [],
        "_note": "Tricky: this is a math question answerable from knowledge (i), but a python_repl tool is available and tempting to use. Tests whether model uses tools as a crutch when not needed.",
    },
]
