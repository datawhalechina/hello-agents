# Chapter 13 Intelligent Travel Assistant

In previous chapters, we built the HelloAgents framework from scratch, implementing core functionalities including various agent paradigms, tool systems, memory mechanisms, protocol communication, and performance evaluation. Starting from this chapter, we will enter a completely new phase: **integrating all learned knowledge to build complete practical applications.**

Do you remember the first agent we built in Chapter 1? It was a simple intelligent travel assistant that demonstrated the basic principles of the `Thought-Action-Observation` loop. The intelligent travel assistant in this chapter will be a complete project, including the following core functions:

**(1) Intelligent Itinerary Planning**: Users input destination, dates, preferences and other information, and the system automatically generates a complete itinerary plan including attractions, dining, and hotels.

**(2) Map Visualization**: Mark attraction locations on the map and draw tour routes, making the itinerary clear at a glance.

**(3) Budget Calculation**: Automatically calculate ticket, hotel, dining, and transportation costs, displaying budget details.

**(4) Itinerary Editing**: Support adding, deleting, and adjusting attractions, updating the map in real-time.

**(5) Export Function**: Support exporting as PDF or image, convenient for saving and sharing.

## 13.1 Project Overview and Architecture Design

### 13.1.1 Why We Need an Intelligent Travel Assistant

Planning a trip is both exciting and frustrating. You need to search for attraction information online, compare different guides, check weather forecasts, book hotels, calculate budgets, and plan routes. This process may take several hours or even days. And even after spending so much time, you're not sure whether the planned itinerary is reasonable, whether you've missed any important attractions, or whether the budget is accurate.

Traditional travel planning methods have several pain points. First is **scattered information**. Attraction information is on travel websites, weather information is on weather websites, hotel information is on booking websites - you need to switch between multiple websites and manually integrate this information. Second is **lack of personalization**. Most guides are generic and don't consider your personal preferences, budget constraints, travel time and other factors. Finally is **difficulty in adjustment**. When you want to modify the itinerary, you may need to replan the entire trip, because the order of attractions, time arrangements, and budget are all interconnected.

AI technology provides new possibilities for solving these problems. Imagine that you only need to tell the system "I want to visit Beijing for 3 days, like history and culture, medium budget", and the system can automatically generate a complete itinerary plan for you, including which attractions to visit each day, where to eat, which hotel to stay at, and how much budget is needed. Moreover, this plan is adjustable - you can delete attractions you don't like, adjust the tour order, and the system will automatically update the map and budget.

This is the intelligent travel assistant we want to build. It's not just a technical demonstration, but a truly useful application. Through this project, you will learn how to apply AI technology to practical problems, how to design multi-agent systems, and how to build complete Web applications.

### 13.1.2 Technical Architecture Overview

The system adopts the classic **front-end and back-end separation architecture**, divided into four layers, as shown in Figure 13.1:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-1.png" alt="" width="85%"/>
  <p>Figure 13.1 Intelligent Travel Assistant Technical Architecture</p>
</div>

**(1) Front-end Layer (Vue3+TypeScript)**: Responsible for user interaction and data display, including form input, result display, and map visualization.

**(2) Back-end Layer (FastAPI)**: Responsible for API routing, data validation, and business logic.

**(3) Agent Layer (HelloAgents)**: Responsible for task decomposition, tool invocation, and result integration. Includes 4 specialized Agents.

**(4) External Service Layer**: Provides data and capabilities, including Amap API, Unsplash API, and LLM API.

The data flow process is as follows: User fills out form on front-end → Back-end validates data → Calls agent system → Agents sequentially call attraction search, weather query, hotel recommendation, itinerary planning Agents → Each Agent calls external APIs through MCP protocol → Integrate results and return to front-end → Front-end renders and displays.

The project structure reference is as follows, provided for easy source code location:
```
helloagents-trip-planner/
├── backend/                    # Backend code
│   ├── app/
│   │   ├── agents/            # Agent implementation
│   │   ├── api/               # API routes
│   │   ├── models/            # Data models
│   │   ├── services/          # Service layer
│   │   └── config.py          # Configuration file
│   └── requirements.txt       # Python dependencies
│
└── frontend/                   # Frontend code
    ├── src/
    │   ├── views/             # Page components
    │   ├── services/          # API services
    │   ├── types/             # Type definitions
    │   └── router/            # Route configuration
    └── package.json           # npm dependencies
```

Detailed architecture design and data flow will be introduced in subsequent sections.

### 13.1.3 Quick Experience: Run the Project in 5 Minutes

Before diving into implementation details, let's first run the project to see the final effect. This way you will have an intuitive understanding of the entire system.

**Environment Requirements:**

- Python 3.10 or higher
- Node.js 16.0 or higher
- npm 8.0 or higher

**Obtain API Keys:**

You need to prepare the following API keys:

- LLM API (OpenAI, DeepSeek, etc.)
- Amap Web Service Key: Visit https://console.amap.com/ to register and create an application
- Unsplash Access Key: Visit https://unsplash.com/developers to register and create an application

Put all API keys in the `.env` file.

Start the backend:

```bash
# 1. Enter backend directory
cd helloagents-trip-planner/backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env file, fill in your API keys

# 4. Start backend service
uvicorn app.api.main:app --reload
# or
python run.py
```

After successful startup, visit http://localhost:8000/docs to see the API documentation.

Open a new terminal window:

```bash
# 1. Enter frontend directory
cd helloagents-trip-planner/frontend

# 2. Install dependencies
npm install

# 3. Start frontend service
npm run dev
```

After successful startup, visit http://localhost:5173 to use the application.

Experience core functions:

First, fill in the destination city, travel dates, preferences, budget, transportation and accommodation types in the homepage form. After clicking the "Start Planning" button, the system will display a loading progress bar and quickly generate a result page, as shown in Figure 13.2.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-2.png" alt="" width="85%"/>
  <p>Figure 13.2 Travel Assistant Planning Progress Page</p>
</div>

After successful loading, the page will clearly display itinerary overview, budget details, attraction map, daily itinerary details and weather information, as shown in Figures 13.3 and 13.4.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-3.png" alt="" width="85%"/>
  <p>Figure 13.3 Travel Assistant Planning Completion Page</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-4.png" alt="" width="85%"/>
  <p>Figure 13.4 Travel Assistant Planning Completion Page</p>
</div>

If users need personalized adjustments, they can click the "Edit Itinerary" button to freely adjust the order of attractions or delete certain attractions, as shown in Figure 13.5. After planning is complete, through the "Export Itinerary" dropdown menu, the final plan can be easily saved as an image or PDF file for convenient reference at any time.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-5.png" alt="" width="85%"/>
  <p>Figure 13.5 Travel Assistant Planning Completion Page</p>
</div>

## 13.2 Data Model Design

### 13.2.1 Data Flow in Web Applications

When building an intelligent travel assistant, we need to solve a core problem: **How to represent and transfer travel plan data?**

We need to understand how data flows in a complete Web application. Imagine what happens when a user clicks the "Start Planning" button in the browser?

The form data filled in by the user on the front-end (destination, dates, budget, etc.) needs to be sent to the back-end server through HTTP requests. After the back-end receives the data, it will call the agent system for processing. The agents will then call external services such as Amap API and Unsplash API to obtain data. The data formats returned by these external APIs are different - some use `lng`, some use `lon`, and some use `longitude`. Finally, the back-end needs to return the processed data to the front-end, which then renders it into the page the user sees.

In this process, data undergoes multiple transformations: Front-end form → HTTP request → Back-end Python object → External API response → Back-end Python object → HTTP response → Front-end TypeScript object → Page display. Without a unified data format, each transformation step could go wrong. This is why we need **data models**.

### 13.2.2 From Dictionaries to Pydantic Models

Let's start with the simple prototype from Chapter 1. In that prototype, we used Python dictionaries to represent attraction data:

```python
# Chapter 1 approach: using dictionaries
attraction = {
    "name": "Forbidden City",
    "location": {"lng": 116.397128, "lat": 39.916527},
    "price": 60
}

# Access data
lng = attraction["location"]["lng"]
```

This approach is convenient in the prototype stage, but will encounter many problems in actual projects. First is the problem of **inconsistent field names**. The location data returned by Amap API is a string like `"116.397128,39.916527"`, which needs to be manually split into longitude and latitude. Unsplash API might use `longitude` and `latitude`. If we use dictionaries everywhere in the code, we need to handle these differences in every place.

Second is the problem of **type safety**. Suppose we accidentally set `price` as a string `"60"`, this won't immediately error in Python, but will cause problems when calculating the total budget. Worse, this kind of error can only be discovered at runtime, and the error message may be difficult to locate.

Finally is the problem of **maintainability**. When we need to add a new field to attractions (such as `rating`), we need to modify multiple places in the code. If we miss somewhere, it will lead to data inconsistency.

Pydantic provides a solution. It is a Python data validation library that allows us to define data structures using classes and automatically handle validation, conversion, and serialization. Let's look at a simple example:

```python
from pydantic import BaseModel, Field

class Location(BaseModel):
    longitude: float = Field(..., description="Longitude")
    latitude: float = Field(..., description="Latitude")

class Attraction(BaseModel):
    name: str
    location: Location
    ticket_price: int = 0

# Create object
attraction = Attraction(
    name="Forbidden City",
    location=Location(longitude=116.397128, latitude=39.916527),
    ticket_price=60
)

# Type-safe access
lng = attraction.location.longitude  # IDE will provide code completion
```

This approach has several benefits. First, if we pass in the wrong type (such as setting `ticket_price` as a string), Pydantic will immediately throw an exception telling us where the error is. Second, the IDE can provide code completion and type checking based on type definitions, greatly reducing spelling errors. Finally, when we need to modify the data structure, we only need to modify the class definition, and all places using this class will automatically update.

### 13.2.3 Core Concepts of Pydantic

Before diving into designing our data models, let's first understand several core concepts of Pydantic. The foundation of Pydantic is the `BaseModel` class, and all data models need to inherit from this class. Each field can specify a type, and Pydantic will automatically perform type checking and conversion.

Field definition uses the `Field` function, which can specify default values, descriptions, validation rules, etc. `...` indicates that this field is required - if this field is not provided when creating an object, Pydantic will throw an exception. We can also use `Optional` to indicate optional fields, or directly provide default values.

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class Attraction(BaseModel):
    name: str = Field(..., description="Attraction name")  # Required
    rating: float = Field(default=0.0, ge=0, le=5)  # Default value, range validation
    visit_duration: int = Field(default=60, gt=0)  # Greater than 0
    description: Optional[str] = None  # Optional field
```

Pydantic also supports nested models and lists. We can use another model as a field type in one model, allowing us to build complex data structures. For example, an attraction contains location information, and an itinerary contains multiple attractions.

```python
class DayPlan(BaseModel):
    date: str
    attractions: List[Attraction]  # Attraction list
    hotel: Optional[Hotel] = None  # Optional hotel information
```

One of the most powerful features is **custom validators**. Sometimes the data format returned by external APIs doesn't meet our requirements, and we can use the `field_validator` decorator to customize validation and conversion logic. For example, the temperature returned by Amap is a string like `"16°C"`, and we need to convert it to a number:

```python
from pydantic import field_validator

class WeatherInfo(BaseModel):
    temperature: int

    @field_validator('temperature', mode='before')
    def parse_temperature(cls, v):
        """Parse temperature string: "16°C" -> 16"""
        if isinstance(v, str):
            v = v.replace('°C', '').replace('℃', '').strip()
            return int(v)
        return v
```

This validator will automatically execute before creating the object, converting the string to an integer. This way we don't need to manually handle temperature format in every place in the code.

### 13.2.4 Bottom-Up Model Design

Now let's start designing the data models for the intelligent travel assistant. A good design principle is **bottom-up**: first define the most basic models, then gradually combine them into complex structures. The advantage of this approach is that each model is simple, easy to understand and maintain.

The most basic model is **location information**. Whether it's attractions, hotels, or restaurants, all need location information. We define a `Location` class to represent longitude and latitude coordinates:

```python
class Location(BaseModel):
    """Location information (longitude and latitude coordinates)"""
    longitude: float = Field(..., description="Longitude", ge=-180, le=180)
    latitude: float = Field(..., description="Latitude", ge=-90, le=90)
```

Here we use range validation (`ge` means greater than or equal to, `le` means less than or equal to) to ensure longitude and latitude values are within reasonable ranges.

Next is **attraction information**. An attraction contains name, address, location, visit duration, description, rating, image, and ticket price information. Note that we use `Location` as a field type, which is a nested model:

```python
class Attraction(BaseModel):
    """Attraction information"""
    name: str = Field(..., description="Attraction name")
    address: str = Field(..., description="Address")
    location: Location = Field(..., description="Longitude and latitude coordinates")
    visit_duration: int = Field(..., description="Recommended visit duration (minutes)", gt=0)
    description: str = Field(..., description="Attraction description")
    category: Optional[str] = Field(default="Attraction", description="Attraction category")
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="Rating")
    image_url: Optional[str] = Field(default=None, description="Image URL")
    ticket_price: int = Field(default=0, ge=0, description="Ticket price (yuan)")
```

Similarly, we define **meal information** and **hotel information**. These models have similar structures, all containing basic information such as name, address, location, and cost:

```python
class Meal(BaseModel):
    """Meal information"""
    type: str = Field(..., description="Meal type: breakfast/lunch/dinner/snack")
    name: str = Field(..., description="Meal name")
    address: Optional[str] = Field(default=None, description="Address")
    location: Optional[Location] = Field(default=None, description="Longitude and latitude coordinates")
    description: Optional[str] = Field(default=None, description="Description")
    estimated_cost: int = Field(default=0, description="Estimated cost (yuan)")

class Hotel(BaseModel):
    """Hotel information"""
    name: str = Field(..., description="Hotel name")
    address: str = Field(default="", description="Hotel address")
    location: Optional[Location] = Field(default=None, description="Hotel location")
    price_range: str = Field(default="", description="Price range")
    rating: str = Field(default="", description="Rating")
    distance: str = Field(default="", description="Distance to attractions")
    type: str = Field(default="", description="Hotel type")
    estimated_cost: int = Field(default=0, description="Estimated cost (yuan/night)")
```

**Budget information** is a special model that doesn't contain location information, but contains a summary of various expenses:

```python
class Budget(BaseModel):
    """Budget information"""
    total_attractions: int = Field(default=0, description="Total attraction ticket cost")
    total_hotels: int = Field(default=0, description="Total hotel cost")
    total_meals: int = Field(default=0, description="Total meal cost")
    total_transportation: int = Field(default=0, description="Total transportation cost")
    total: int = Field(default=0, description="Total cost")
```

Now we can combine these basic models to build a **daily itinerary**. A daily itinerary contains date, description, transportation method, accommodation arrangement, hotel, attraction list, and meal list:

```python
class DayPlan(BaseModel):
    """Daily itinerary"""
    date: str = Field(..., description="Date")
    day_index: int = Field(..., description="Day number (starting from 0)")
    description: str = Field(..., description="Daily itinerary description")
    transportation: str = Field(..., description="Transportation method")
    accommodation: str = Field(..., description="Accommodation arrangement")
    hotel: Optional[Hotel] = Field(default=None, description="Hotel information")
    attractions: List[Attraction] = Field(default_factory=list, description="Attraction list")
    meals: List[Meal] = Field(default_factory=list, description="Meal arrangements")
```

Note that we use `List[Attraction]` to represent the attraction list, and `default_factory=list` means the default value is an empty list.

**Weather information** requires special handling because the temperature format returned by Amap is non-standard. We use a custom validator to handle this:

```python
class WeatherInfo(BaseModel):
    """Weather information"""
    date: str = Field(..., description="Date")
    day_weather: str = Field(..., description="Daytime weather")
    night_weather: str = Field(..., description="Nighttime weather")
    day_temp: int = Field(..., description="Daytime temperature (Celsius)")
    night_temp: int = Field(..., description="Nighttime temperature (Celsius)")
    wind_direction: str = Field(..., description="Wind direction")
    wind_power: str = Field(..., description="Wind power")

    @field_validator('day_temp', 'night_temp', mode='before')
    def parse_temperature(cls, v):
        """Parse temperature string: "16°C" -> 16"""
        if isinstance(v, str):
            v = v.replace('°C', '').replace('℃', '').replace('°', '').strip()
            try:
                return int(v)
            except ValueError:
                return 0  # Error tolerance
        return v
```

Finally, we define the **complete travel plan**. This is the top-level model that contains all information:

```python
class TripPlan(BaseModel):
    """Travel plan"""
    city: str = Field(..., description="Destination city")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    days: List[DayPlan] = Field(default_factory=list, description="Daily itinerary")
    weather_info: List[WeatherInfo] = Field(default_factory=list, description="Weather information")
    overall_suggestions: str = Field(..., description="Overall suggestions")
    budget: Optional[Budget] = Field(default=None, description="Budget information")
```

This way, we have completed the design of the entire data model. From the most basic `Location`, to `Attraction`, `Meal`, `Hotel`, then to `DayPlan`, and finally to `TripPlan`, forming a clear hierarchical structure.

### 13.2.5 Application of Data Models in Web Applications

Now let's see how these data models are used in actual Web applications. In FastAPI, Pydantic models can be directly used as type definitions for requests and responses. FastAPI will automatically perform data validation, serialization, and documentation generation.

```python
from fastapi import FastAPI
from app.models.schemas import TripPlanRequest, TripPlan

app = FastAPI()

@app.post("/api/trip/plan", response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    """
    Create travel plan

    FastAPI automatically:
    1. Validates request data (TripPlanRequest)
    2. Validates response data (TripPlan)
    3. Generates OpenAPI documentation
    """
    trip_plan = await generate_trip_plan(request)
    return trip_plan
```

When a user sends a POST request to `/api/trip/plan`, FastAPI will automatically convert the JSON data into a `TripPlanRequest` object. If the data format is incorrect (such as missing required fields or type mismatch), FastAPI will automatically return a 400 error and tell the user where the error is.

On the front-end, we also need to define corresponding TypeScript types. Although TypeScript and Python are different languages, the data structures are the same:

```typescript
interface Location {
  longitude: number;
  latitude: number;
}

interface Attraction {
  name: string;
  address: string;
  location: Location;
  visit_duration: number;
  ticket_price: number;
}

interface TripPlan {
  city: string;
  start_date: string;
  end_date: string;
  days: DayPlan[];
}
```

This way, the front-end and back-end use a unified data format. When the back-end returns a `TripPlan` object, the front-end can use it directly without any conversion. TypeScript's type checking can also help us avoid many errors.

## 13.3 Multi-Agent Collaboration Design

### 13.3.1 Why We Need Multi-Agent

In Chapter 7, we learned how to build agents using SimpleAgent. The design philosophy of SimpleAgent is simple and direct: each time the `run()` method is called, the Agent analyzes the user's question, decides whether to call tools, and then returns the result. This design is very effective when handling simple tasks, but when facing tasks like travel planning, some problems arise.

If we use a single Agent to complete travel planning, what does this Agent need to do? First, it needs to search for attraction information, which requires calling Amap's POI search tool. Then, it needs to query weather information, which requires calling the weather query tool. Next, it needs to search for hotel information, which again requires calling the POI search tool. Finally, it needs to integrate all this information to generate a complete travel plan.

This sounds simple, but in actual operation, the first problem is encountered: **tool calling limitations**. SimpleAgent can only execute one tool per `run()` call. This means we need to call the `run()` method multiple times, with each call handling one task. But this brings a new problem: how to pass information between multiple calls? How to pass the attraction information obtained from the first call to the second call? We need to manually manage these intermediate results, and the code becomes very complex.

Of course, we can use ReactAgent to solve this problem. ReactAgent can execute multiple tools in one call, and it will automatically perform multiple rounds of thinking and action. But this brings new problems: **time cost**. Each round of thinking by ReactAgent requires calling the LLM. If three tools need to be called, at least three rounds of thinking are needed, which means at least three LLM calls. Moreover, these calls are serial - the next one can only start after the previous one is complete, so the total time will be very long.

The second problem is **prompt complexity**. If we want one Agent to complete all tasks, we need to describe the execution logic of each task in detail in the prompt. For example:

```python
COMPLEX_PROMPT = """You are a travel planning assistant. You need to:
1. Use maps_text_search to search for attractions, keywords determined by user preferences
2. Use maps_weather to query weather, get weather forecast for the next few days
3. Use maps_text_search to search for hotels, type determined by user needs
4. Integrate all information to generate travel plan, including daily attractions, dining, accommodation arrangements
Note: Must execute in order, each tool can only be called once, output must be in JSON format...
"""
```

This kind of prompt has several problems. First is **difficult to maintain**. If we want to modify the attraction search logic (such as adding rating filtering), we need to modify the entire prompt, which can easily affect other parts. Second is **error-prone**. The LLM needs to understand the requirements of multiple tasks simultaneously, and can easily confuse the formats and parameters of different tasks. Finally is **difficult to debug**. When the generated plan doesn't meet expectations, it's hard to know which part went wrong - is the attraction search inaccurate, did the weather query fail, or is there a problem with the integration logic?

Facing these problems, a natural idea is: can we decompose complex tasks into multiple simple tasks and let different Agents each do their own job? This is the core idea of multi-Agent collaboration.

Imagine a travel agency in the real world. When you go to a travel agency to consult about a travel plan, you won't be served by just one person. Usually there will be a dedicated attraction consultant responsible for recommending attractions; a hotel consultant responsible for booking hotels; and an itinerary planner responsible for integrating all information into a complete itinerary. Each person focuses on their area of expertise, and finally the itinerary planner summarizes all the information. This division of labor and collaboration is much more efficient than having one person do everything.

### 13.3.2 Agent Role Design

Based on the task decomposition principle, we designed four specialized Agents, as shown in Figure 13.6:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-6.png" alt="" width="85%"/>
  <p>Figure 13.6 Multi-Agent Collaboration Flow</p>
</div>

- **AttractionSearchAgent (Attraction Search Expert)** focuses on searching for attraction information. It only needs to understand user preferences (such as "history and culture", "natural scenery"), then call Amap's POI search tool and return a list of related attractions. Its prompt is very simple, only needing to explain how to choose keywords based on preferences and how to call tools.

- **WeatherQueryAgent (Weather Query Expert)** focuses on querying weather information. It only needs to know the city name, then call the weather query tool and return the weather forecast for the next few days. Its task is very clear and almost error-free.

- **HotelAgent (Hotel Recommendation Expert)** focuses on searching for hotel information. It needs to understand user accommodation needs (such as "budget", "luxury"), then call the POI search tool and return a list of hotels that meet the requirements.

- **PlannerAgent (Itinerary Planning Expert)** is responsible for integrating all information. It receives the output from the first three Agents, plus the user's original requirements (dates, budget, etc.), and then generates a complete travel plan. It doesn't need to call any external tools, only needs to focus on information integration and itinerary arrangement.

Now let's design the role and prompt for each Agent in detail. When designing prompts, we need to consider several key questions: What input does this Agent need? What output should it produce? What tools does it need to call? What problems might it encounter?

**AttractionSearchAgent**'s task is to search for attractions based on user preferences. Its input is the city name and user preferences (such as "history and culture", "natural scenery"). It needs to call the `amap_maps_text_search` tool with parameters being keywords and city. Its output is a list of attractions, including name, address, rating, and other information.

```python
ATTRACTION_AGENT_PROMPT = """You are an attraction search expert.

**Tool Call Format:**
`[TOOL_CALL:amap_maps_text_search:keywords=attraction,city=city_name]`

**Examples:**
- `[TOOL_CALL:amap_maps_text_search:keywords=attraction,city=Beijing]`
- `[TOOL_CALL:amap_maps_text_search:keywords=museum,city=Shanghai]`

**Important:**
- Must use tools to search, don't fabricate information
- Search for attractions in {city} based on user preferences ({preferences})
"""
```

This prompt is concise but contains all necessary information. It clearly explains the tool call format, provides specific examples, and emphasizes two important principles: must use tools (can't fabricate) and search based on user preferences.

**WeatherQueryAgent**'s task is simpler, only needing to query weather. Its input is the city name, and output is weather information.

```python
WEATHER_AGENT_PROMPT = """You are a weather query expert.

**Tool Call Format:**
`[TOOL_CALL:amap_maps_weather:city=city_name]`

Please query weather information for {city}.
"""
```

**HotelAgent**'s task is to search for hotels. Its input is the city name and accommodation type, and output is a hotel list.

```python
HOTEL_AGENT_PROMPT = """You are a hotel recommendation expert.

**Tool Call Format:**
`[TOOL_CALL:amap_maps_text_search:keywords=hotel,city=city_name]`

Please search for {accommodation} hotels in {city}.
"""
```

**PlannerAgent** is the most complex because it needs to integrate all information. Its input is user requirements and the output from the first three Agents, and output is a complete travel plan (JSON format).

```python
PLANNER_AGENT_PROMPT = """You are an itinerary planning expert.

**Output Format:**
Strictly return in the following JSON format:
{
  "city": "city name",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [...],
  "weather_info": [...],
  "overall_suggestions": "overall suggestions",
  "budget": {...}
}

**Planning Requirements:**
1. weather_info must include weather for each day
2. Temperature as pure numbers (without °C)
3. Arrange 2-3 attractions per day
4. Consider attraction distance and visit time
5. Include breakfast, lunch, and dinner
6. Provide practical suggestions
7. Include budget information
"""
```

### 13.3.3 Agent Collaboration Flow

Now let's see how these four Agents collaborate to complete the travel planning task. The entire flow can be divided into five steps:

```python
class TripPlannerAgent:
    def __init__(self):
        self.attraction_agent = SimpleAgent(name="Attraction Search", prompt=ATTRACTION_PROMPT)
        self.weather_agent = SimpleAgent(name="Weather Query", prompt=WEATHER_PROMPT)
        self.hotel_agent = SimpleAgent(name="Hotel Recommendation", prompt=HOTEL_PROMPT)
        self.planner_agent = SimpleAgent(name="Itinerary Planning", prompt=PLANNER_PROMPT)

    def plan_trip(self, request: TripPlanRequest) -> TripPlan:
        # Step 1: Attraction search
        attraction_response = self.attraction_agent.run(
            f"Please search for {request.preferences} attractions in {request.city}"
        )

        # Step 2: Weather query
        weather_response = self.weather_agent.run(
            f"Please query weather for {request.city}"
        )

        # Step 3: Hotel recommendation
        hotel_response = self.hotel_agent.run(
            f"Please search for {request.accommodation} hotels in {request.city}"
        )

        # Step 4: Integrate and generate plan
        planner_query = self._build_planner_query(
            request, attraction_response, weather_response, hotel_response
        )
        planner_response = self.planner_agent.run(planner_query)

        # Step 5: Parse JSON
        trip_plan = self._parse_trip_plan(planner_response)
        return trip_plan
```

This flow executes four steps sequentially, with the output of each step serving as input for the next step. Note that we use the `TripPlanRequest` and `TripPlan` Pydantic models defined in Section 13.2.

### 13.3.4 Query Construction

PlannerAgent needs to integrate all information. This query needs to include all necessary information and be organized clearly and orderly so that the LLM can accurately understand it.

```python
def _build_planner_query(
    self,
    request: TripPlanRequest,
    attraction_response: str,
    weather_response: str,
    hotel_response: str
) -> str:
    """Build query for planning Agent"""
    return f"""
Please generate a {request.days}-day travel plan for {request.city} based on the following information:

**User Requirements:**
- Destination: {request.city}
- Dates: {request.start_date} to {request.end_date}
- Days: {request.days} days
- Preferences: {request.preferences}
- Budget: {request.budget}
- Transportation: {request.transportation}
- Accommodation: {request.accommodation}

**Attraction Information:**
{attraction_response}

**Weather Information:**
{weather_response}

**Hotel Information:**
{hotel_response}

Please generate a detailed travel plan, including daily attraction arrangements, dining recommendations, accommodation information, and budget details.
"""
```

Through this multi-Agent collaboration design, we decompose a complex travel planning task into four simple subtasks. Each Agent focuses on its area of expertise, and also lays a good foundation for future feature expansion (such as adding restaurant recommendation Agent, transportation planning Agent).

## 13.4 MCP Tool Integration Details

### 13.4.1 Why Not Call APIs Directly

In Section 13.3, we designed four Agents to collaborate on the travel planning task. Among them, AttractionSearchAgent, WeatherQueryAgent, and HotelAgent all need to call Amap's API to obtain data. A natural question is: why not call Amap's HTTP API directly in the Agent?

Let's first see what calling the API directly would look like. Amap provides a POI search API, and we need to construct HTTP requests, pass parameters, and parse responses:

```python
import requests

def search_poi(keywords: str, city: str, api_key: str):
    """Directly call Amap POI search API"""
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keywords,
        "city": city,
        "key": api_key,
        "output": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data
```

This approach looks simple, but will encounter several problems in actual use. First is **Agent cannot call autonomously**. In our HelloAgents framework, Agents call tools by recognizing tool call markers in prompts (such as `[TOOL_CALL:tool_name:arg1=value1]`). If we call the API directly in code, the Agent loses its autonomous decision-making ability and becomes a simple function call.

Second is **complex parameter passing**. Amap's API has many parameters. For example, POI search has more than a dozen parameters such as `keywords`, `city`, `types`, `offset`, `page`, etc. If we want the Agent to use these parameters flexibly, we need to explain the meaning and format of each parameter in detail in the prompt, which will make the prompt very complex.

Third is **difficult response parsing**. The data returned by Amap API is in JSON format with a relatively complex structure. We need to write code to parse this data and extract the fields we need. If the API's response format changes, we need to modify the parsing code.

Finally is **chaotic tool management**. Amap provides more than a dozen different APIs (POI search, weather query, route planning, etc.). If we write a function for each API and then manually register it to the Agent's tool list, the code will become very lengthy. And when we want to add a new API, we need to modify multiple places.

### 13.4.2 Amap MCP Integration

MCP (Model Context Protocol) is a standardized protocol proposed by Anthropic for connecting LLMs and external tools. This section will introduce how to integrate the Amap MCP server in the project. Our project uses `amap-mcp-server`, which is an MCP server implemented in Node.js:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-7.png" alt="" width="85%"/>
  <p>Figure 13.7 amap-mcp-server Tools</p>
</div>

The Amap MCP server provides various tools, mainly divided into the following categories, as shown in Table 13.1:

<div align="center">
  <p>Table 13.1 Amap MCP Tool Categories</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-table-1.png" alt="" width="85%"/>
</div>

Through the MCP protocol, we can easily integrate in HelloAgents:

```python
from hello_agents.tools import MCPTool
from app.config import get_settings

settings = get_settings()

# Create MCP tool
mcp_tool = MCPTool(
    name="amap_mcp",
    command="npx",
    args=["-y", "@sugarforever/amap-mcp-server"],
    env={"AMAP_API_KEY": settings.amap_api_key},
    auto_expand=True
)
```

What does this code do? First, `command` and `args` specify how to start the MCP server. `npx -y @sugarforever/amap-mcp-server` will download and run the `amap-mcp-server` package from the npm repository. The `env` parameter passes environment variables, here we pass the Amap API key.

**Note:** Some examples in this document use `npx` to launch MCP (Model Context Protocol) services. However,in the code repository corresponding to this section of content, we actually use `uvx`. It’s important to note that `npx` and `uvx` share nearly identical design principles—the only difference lies in their ecosystems: `npx` targets JavaScript/Node.js (packages from npm), while `uvx` targets Python (packages from PyPI).There is no superiority or inferiority between the two methods. Please choose according to your needs when using them.

When we create the `MCPTool` object, it will start the MCP server process in the background and communicate with the server through standard input/output (stdin/stdout). This is a feature of the MCP protocol: using inter-process communication instead of HTTP, which is more efficient and easier to manage.

The most critical parameter is `auto_expand=True`. When set to True, `MCPTool` will automatically query what tools the MCP server provides, and then create an independent Tool object for each tool. This is why we only created one `MCPTool`, but the Agent got 16 tools. Let's see this process:

```python
# Create one MCPTool
mcp_tool = MCPTool(..., auto_expand=True)
agent.add_tool(mcp_tool)

# Agent actually gets 16 tools!
print(list(agent.tools.keys()))
# ['amap_maps_text_search', 'amap_maps_weather', ...]
```

As shown in Figure 13.8, suppose the user wants to search for attractions in Beijing. AttractionSearchAgent receives the query "Please search for historical and cultural attractions in Beijing". The Agent analyzes this query and decides to call the `amap_maps_text_search` tool with parameters `keywords=attraction, city=Beijing`.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-8.png" alt="" width="85%"/>
  <p>Figure 13.8 MCP Tool Call Flow</p>
</div>

The Agent generates a tool call marker: `[TOOL_CALL:amap_maps_text_search:keywords=attraction,city=Beijing]`. The HelloAgents framework parses this marker, extracts the tool name and parameters, and then calls the corresponding Tool object.

The Tool object is automatically created by `MCPTool`, and it will send the call request to the MCP server. Specifically, it will construct a JSON-RPC format message and send it to the server process through stdin:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "amap_maps_text_search",
    "arguments": {
      "keywords": "attraction",
      "city": "Beijing"
    }
  }
}
```

The MCP server receives this message, parses the parameters, and then calls Amap's HTTP API. It will construct an HTTP request, add the API key, send the request, and receive the response.

Amap API returns JSON format data containing attraction list, address, coordinates, and other information. The MCP server parses this data, extracts key fields, and then constructs a response message, returning it to `MCPTool` through stdout:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found the following attractions:\n1. Forbidden City Museum - Address: No. 4 Jingshan Front Street, Dongcheng District\n2. Temple of Heaven Park - Address: Tiantan Road, Dongcheng District\n..."
      }
    ]
  }
}
```

`MCPTool` receives the response, extracts the text content, and returns it to the Agent. The Agent uses this result as the output of the tool call and continues to generate the final reply.

This process looks complex, but for the Agent, it only needs to know that there is a tool called `amap_maps_text_search` that can search for attractions. All the underlying details are encapsulated by the MCP protocol and `MCPTool`.

### 13.4.3 Sharing MCP Instances

In our multi-Agent system, three Agents all need to use Amap tools. So should each Agent create its own `MCPTool` instance, or share the same instance?

If each Agent creates a `MCPTool` instance, this means three server processes will run simultaneously. Each process will independently call the Amap API, which may exceed the API's rate limit. Moreover, multiple processes will occupy more memory and CPU resources.

A better approach is to let all Agents share the same `MCPTool` instance. This way, only one MCP server process needs to be started, and all API calls go through this process. This not only saves resources but also allows better control of API call frequency.

In the code, we create a `MCPTool` instance in the constructor of `TripPlannerAgent`, and then add it to each sub-Agent's tool list:

```python
class TripPlannerAgent:
    def __init__(self):
        settings = get_settings()
        self.llm = HelloAgentsLLM()

        # Create shared MCP tool instance (create only once)
        self.mcp_tool = MCPTool(
            name="amap_mcp",
            command="npx",
            args=["-y", "@sugarforever/amap-mcp-server"],
            env={"AMAP_API_KEY": settings.amap_api_key},
            auto_expand=True
        )

        # Create multiple Agents, sharing the same MCP tool
        self.attraction_agent = SimpleAgent(
            name="AttractionSearchAgent",
            llm=self.llm,
            system_prompt=ATTRACTION_AGENT_PROMPT
        )
        self.attraction_agent.add_tool(self.mcp_tool)  # Share

        self.weather_agent = SimpleAgent(
            name="WeatherQueryAgent",
            llm=self.llm,
            system_prompt=WEATHER_AGENT_PROMPT
        )
        self.weather_agent.add_tool(self.mcp_tool)  # Share

        self.hotel_agent = SimpleAgent(
            name="HotelAgent",
            llm=self.llm,
            system_prompt=HOTEL_AGENT_PROMPT
        )
        self.hotel_agent.add_tool(self.mcp_tool)  # Share
```

This way, all three Agents can use Amap's 16 tools, but only one MCP server process is running underneath. When we call the `plan_trip` method of `TripPlannerAgent`, the three Agents will call tools in sequence, and all requests are sent to the Amap API through the same MCP server.

### 13.4.4 Unsplash Image API Integration

In addition to Amap, we also need to obtain images for attractions to make the travel plan more vivid and intuitive. We use the Unsplash API to search for attraction images. Note that Unsplash is a foreign service and is one of the few image APIs that can be used for free, so search results may not be accurate enough. In actual projects, you can consider using Bing, Baidu, or Amap's POI image API, but these services usually require payment.

The integration of Unsplash API is relatively simple. We create an `UnsplashService` class to encapsulate API calls:

```python
# backend/app/services/unsplash_service.py
import requests
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class UnsplashService:
    """Unsplash image service"""

    def __init__(self, access_key: str):
        self.access_key = access_key
        self.base_url = "https://api.unsplash.com"

    def search_photos(self, query: str, per_page: int = 10) -> List[Dict]:
        """Search for images"""
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Extract image URLs
            photos = []
            for result in results:
                photos.append({
                    "url": result["urls"]["regular"],
                    "description": result.get("description", ""),
                    "photographer": result["user"]["name"]
                })

            return photos

        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []

    def get_photo_url(self, query: str) -> Optional[str]:
        """Get single image URL"""
        photos = self.search_photos(query, per_page=1)
        return photos[0].get("url") if photos else None
```

This service class provides two methods: `search_photos` searches for multiple images, and `get_photo_url` gets the URL of a single image. We use this service in the API route to get images for each attraction:

```python
# backend/app/api/routes/trip.py
from app.services.unsplash_service import UnsplashService

unsplash_service = UnsplashService(settings.unsplash_access_key)

@router.post("/plan", response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    # Generate travel plan
    trip_plan = trip_planner_agent.plan_trip(request)

    # Get images for each attraction
    for day in trip_plan.days:
        for attraction in day.attractions:
            if not attraction.image_url:
                image_url = unsplash_service.get_photo_url(
                    f"{attraction.name} {trip_plan.city}"
                )
                attraction.image_url = image_url

    return trip_plan
```

Note that we didn't encapsulate Unsplash as a Tool or MCP tool, but called it directly in the API route. This is because image search doesn't require the Agent's intelligent decision-making, it's just a simple data enhancement step. If you want the Agent to autonomously decide whether images are needed or choose different image sources, you can consider encapsulating it as a Tool.

## 13.5 Front-End Development Details

### 13.5.1 Front-End and Back-End Separation Web Architecture

Before starting front-end development, we need to understand the architecture pattern of modern Web applications. In early Web development, front-end and back-end were mixed together. For example, technologies like PHP and JSP had HTML templates and business logic code written in the same file. This approach is convenient in small projects, but encounters many problems in large projects: front-end and back-end developers need frequent coordination, code is difficult to reuse, and testing is difficult.

Modern Web applications generally adopt a **front-end and back-end separation** architecture. The back-end is only responsible for providing API interfaces and returning data in JSON format. The front-end is an independent application that calls back-end APIs through HTTP requests, obtains data, and then renders pages. This architecture has several obvious advantages: front-end and back-end can be developed, deployed, and tested independently; the front-end can be a Web application, mobile application, or desktop application, all using the same set of back-end APIs; the front-end can use modern frameworks and toolchains to provide a better user experience.

In our intelligent travel assistant project, the back-end is implemented with Python and FastAPI, providing a core API interface `POST /api/trip/plan` that receives travel requirements and returns travel plans. The front-end is implemented with Vue 3 and TypeScript, and is a single-page application (SPA). Users fill in forms in the browser, click the "Start Planning" button, the front-end sends an HTTP request to the back-end, waits for a response, and then renders the result page. Throughout this process, the page doesn't refresh, and the user experience is very smooth.

The choice of front-end technology stack needs to consider several factors: development efficiency, performance, ecosystem, and learning curve. As shown in Table 13.2, the project chose the following technology stack:

<div align="center">
  <p>Table 13.2 Front-End Technology Stack</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-table-2.png" alt="" width="85%"/>
</div>

The project's directory structure is as follows:

```
frontend/
├── src/
│   ├── views/              # Page components
│   │   ├── Home.vue        # Home page (form)
│   │   └── Result.vue      # Result page
│   ├── services/           # API services
│   │   └── api.ts
│   ├── types/              # Type definitions
│   │   └── index.ts
│   ├── router/             # Router configuration
│   │   └── index.ts
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

The `views` directory stores page components, the `services` directory stores API call logic, the `types` directory stores TypeScript type definitions, and the `router` directory stores router configuration.

### 13.5.2 Type Definitions

In Section 13.2, we used Pydantic to define data models on the back-end, such as `Location`, `Attraction`, `DayPlan`, `TripPlan`, etc. On the front-end, we need to define corresponding TypeScript types.

Let's see how to define these types. First is the most basic `Location` type, representing longitude and latitude coordinates:

```typescript
// frontend/src/types/index.ts
export interface Location {
  longitude: number
  latitude: number
}
```

This type definition corresponds exactly to the back-end Pydantic model. Note that TypeScript uses the `interface` keyword to define types, field types are separated by colons, and no default values are needed.

Next is the `Attraction` type, representing attraction information:

```typescript
export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  image_url?: string
  ticket_price?: number
}
```

Note that we use the `Location` type as a field type here, which is a nested type. The question mark `?` indicates an optional field, corresponding to `Optional` in the back-end Pydantic model.

Similarly, we define types like `Meal`, `Hotel`, `Budget`, `WeatherInfo`, etc. Finally, the top-level `TripPlan` type:

```typescript
export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}
```

There's also the request type `TripPlanRequest`, corresponding to the back-end request model:

```typescript
export interface TripPlanRequest {
  city: string
  start_date: string
  end_date: string
  days: number
  preferences: string
  budget: string
  transportation: string
  accommodation: string
}
```

What are these type definitions for? First, when we call the API, TypeScript will check whether the data we pass conforms to the `TripPlanRequest` type. If we accidentally write `days` as a string, TypeScript will immediately report an error. Second, when we receive the API response, TypeScript will check whether the response data conforms to the `TripPlan` type. If the back-end's data structure changes, the front-end will immediately discover it. Finally, the IDE can provide code completion based on type definitions. When we type `tripPlan.`, the IDE will automatically list all available fields.

### 13.5.3 API Service Encapsulation

With type definitions, we can encapsulate API calls. We create an `api.ts` file and use Axios to send HTTP requests:

```typescript
import axios from 'axios'
import type { TripPlanRequest, TripPlan } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000, // 2-minute timeout
  headers: {
    'Content-Type': 'application/json'
  }
})
```

Here we create an Axios instance and configure the base URL, timeout, and request headers. Why is the timeout set to 2 minutes? Because generating a travel plan requires calling multiple Agents, each Agent needs to call the LLM and external APIs, and the entire process may take 10-30 seconds. If the timeout is too short, the request will be interrupted.

Next we add interceptors. Interceptors can execute some common logic before sending requests and after receiving responses, such as logging, error handling, authentication, etc.:

```typescript
// Request interceptor
api.interceptors.request.use(
  config => {
    console.log('Sending request:', config)
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  response => {
    console.log('Received response:', response)
    return response
  },
  error => {
    console.error('Request failed:', error)
    return Promise.reject(error)
  }
)
```

Finally, we define the API function, which is the only entry point for the front-end to call the back-end:

```typescript
// Generate travel plan
export const generateTripPlan = async (request: TripPlanRequest): Promise<TripPlan> => {
  const response = await api.post<TripPlan>('/trip/plan', request)
  return response.data
}
```

Note the type signature of this function: the parameter is of type `TripPlanRequest`, and the return value is of type `Promise<TripPlan>`. This means TypeScript will check whether the parameters passed by the caller meet the requirements, and will also check whether the use of the return value is correct.

### 13.5.4 Home Form Design

The Home page is the user's entry point, containing a form for users to fill in travel requirements. We use Vue 3's Composition API to organize the code:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { generateTripPlan } from '@/services/api'
import type { TripPlanRequest } from '@/types'

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const formData = ref<TripPlanRequest>({
  city: '',
  start_date: '',
  end_date: '',
  days: 3,
  preferences: 'History and Culture',
  budget: 'Medium',
  transportation: 'Public Transportation',
  accommodation: 'Budget Hotel'
})
</script>
```

Here we use `ref` to create reactive variables. `formData` is the form data, of type `TripPlanRequest`. `loading` indicates whether it's loading, `loadingProgress` indicates the loading progress, and `loadingStatus` indicates the loading status text.

The form submission logic is as follows:

```typescript
const handleSubmit = async () => {
  loading.value = true
  loadingProgress.value = 0

  // Simulate progress updates
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = '🔍 Searching for attractions...'
      else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ Querying weather...'
      else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 Recommending hotels...'
      else loadingStatus.value = '📋 Generating itinerary...'
    }
  }, 500)

  try {
    const response = await generateTripPlan(formData.value)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    router.push({ name: 'result', state: { tripPlan: response } })
  } catch (error) {
    clearInterval(progressInterval)
    message.error('Failed to generate plan, please try again')
  } finally {
    loading.value = false
  }
}
```

This code does several things. First, it sets `loading` to true to display the loading state. Then, it starts a timer that updates the progress bar and status text every 500 milliseconds. This is a simulated progress because we can't accurately know the back-end's processing progress. But this lets users know the system is working, rather than being stuck.

Next, it calls the `generateTripPlan` function to send the API request. This is an asynchronous operation, and we use `await` to wait for the response. If the request succeeds, clear the timer, set progress to 100%, then navigate to the result page and pass the travel plan data. If the request fails, display an error message. Finally, whether successful or failed, set `loading` to false to hide the loading state.

The template part uses Ant Design Vue components:

```vue
<template>
  <div class="home-container">
    <div class="page-header">
      <h1 class="page-title">✈️ Intelligent Travel Assistant</h1>
      <p class="page-subtitle">AI-Powered Personalized Travel Planning</p>
    </div>

    <a-card class="form-card">
      <a-form :model="formData" @finish="handleSubmit">
        <a-form-item label="Destination City" name="city" :rules="[{ required: true }]">
          <a-input v-model:value="formData.city" placeholder="e.g., Beijing" />
        </a-form-item>

        <!-- More form items... -->

        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" :loading="loading">
            Start Planning
          </a-button>
        </a-form-item>

        <!-- Loading progress bar -->
        <a-form-item v-if="loading">
          <a-progress :percent="loadingProgress" status="active" />
          <p>{{ loadingStatus }}</p>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>
```

Note the `v-model:value` directive, which implements two-way data binding. When users type in the input box, `formData.city` automatically updates. When the value of `formData.city` changes, the input box content also automatically updates.

### 13.5.5 Result Page Display

The Result page is the core of the entire application, displaying the generated travel plan. This page includes several parts: itinerary overview, budget details, map visualization, daily itinerary details, and weather information.

First is map visualization. We use the Amap JS API to mark attraction locations on the map:

```typescript
import AMapLoader from '@amap/amap-jsapi-loader'

const initMap = async () => {
  const AMap = await AMapLoader.load({
    key: 'your_amap_web_key',
    version: '2.0'
  })

  map = new AMap.Map('amap-container', {
    zoom: 12,
    center: [116.397128, 39.916527]
  })

  // Add attraction markers
  tripPlan.value.days.forEach((day) => {
    day.attractions.forEach((attraction, index) => {
      const marker = new AMap.Marker({
        position: [attraction.location.longitude, attraction.location.latitude],
        title: attraction.name,
        label: { content: `${index + 1}`, direction: 'top' }
      })
      map.add(marker)
    })
  })
}
```

This code first loads the Amap SDK, then creates a map instance, and finally iterates through all attractions to create a marker for each. The marker's position is the attraction's longitude and latitude coordinates, which are obtained from the back-end's `Attraction` object.

The export function uses the `html2canvas` and `jsPDF` libraries. `html2canvas` can convert DOM elements to Canvas, and then we can export the Canvas as an image or PDF:

```typescript
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

// Export as image
const exportAsImage = async () => {
  const element = document.getElementById('trip-plan-content')
  const canvas = await html2canvas(element, { scale: 2 })
  const link = document.createElement('a')
  link.download = `${tripPlan.value.city} Travel Plan.png`
  link.href = canvas.toDataURL()
  link.click()
}

// Export as PDF
const exportAsPDF = async () => {
  const element = document.getElementById('trip-plan-content')
  const canvas = await html2canvas(element, { scale: 2 })
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF('p', 'mm', 'a4')
  const imgWidth = 210
  const imgHeight = (canvas.height * imgWidth) / canvas.width
  pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)
  pdf.save(`${tripPlan.value.city} Travel Plan.pdf`)
}
```

Through these front-end technologies, we implemented a complete Web application. Users can fill in forms in the browser, submit requests, wait for AI to generate travel plans, then view detailed itinerary arrangements, see attraction locations on the map, and export as images or PDFs. The entire process is smooth and natural - this is the charm of modern Web applications.

## 13.6 Feature Implementation Details

This section introduces the core feature implementations of the intelligent travel assistant, including budget calculation, loading progress bar, itinerary editing, export functionality, and side navigation.

### 13.6.1 Budget Calculation Feature

When planning a trip, budget is a very important consideration. Users need to know approximately how much this trip will cost and where the money will be spent. Our intelligent travel assistant provides automatic budget calculation functionality, dividing expenses into four major categories: attraction tickets, hotel accommodation, dining, and transportation.

Where is the budget calculation logic implemented? We chose to implement it in the back-end's PlannerAgent. Why not calculate on the front-end? Because budget estimation needs to be based on attraction ticket prices, hotel price ranges, dining standards, and other information, all of which are already obtained by PlannerAgent when generating the itinerary. If calculated on the front-end, we would need to duplicate this logic, and it might not be accurate.

In PlannerAgent's prompt, we explicitly require the LLM to generate budget information:

```python
PLANNER_AGENT_PROMPT = """
You are an itinerary planning expert.

**Output Format:**
Strictly return in the following JSON format:
{
  ...
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}

**Planning Requirements:**
...
7. Include budget information, estimate based on attraction tickets, hotel prices, dining standards, and transportation methods
"""
```

The LLM will estimate the cost of each item based on the attractions, hotels, and dining arrangements in the itinerary. For example, if the itinerary includes the Forbidden City (ticket 60 yuan), Temple of Heaven (ticket 15 yuan), and Summer Palace (ticket 30 yuan), then the total attraction ticket cost is 105 yuan. If it's a 3-day 2-night trip with budget hotels (300 yuan per night), then the total hotel cost is 600 yuan.

On the front-end, we use Ant Design Vue's Statistic component to display budget information. This component is specifically designed for displaying statistical data and supports number animations, prefixes/suffixes, custom styles, etc.:

```vue
<a-card v-if="tripPlan.budget" title="💰 Budget Details">
  <a-row :gutter="16">
    <a-col :span="6">
      <a-statistic title="Attraction Tickets" :value="tripPlan.budget.total_attractions" suffix="yuan" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="Hotel Accommodation" :value="tripPlan.budget.total_hotels" suffix="yuan" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="Dining Expenses" :value="tripPlan.budget.total_meals" suffix="yuan" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="Transportation" :value="tripPlan.budget.total_transportation" suffix="yuan" />
    </a-col>
  </a-row>
  <a-divider />
  <a-row>
    <a-col :span="24" style="text-align: center;">
      <a-statistic
        title="Estimated Total Cost"
        :value="tripPlan.budget.total"
        suffix="yuan"
        :value-style="{ color: '#cf1322', fontSize: '32px', fontWeight: 'bold' }"
      />
    </a-col>
  </a-row>
</a-card>
```

This code uses grid layout (`a-row` and `a-col`) to display the four expense items side by side. Each expense item uses an `a-statistic` component to display the title and value. Finally, a divider (`a-divider`) separates them, and below displays the total cost in large red font for emphasis.

Note the conditional rendering `v-if="tripPlan.budget"`. Because budget information is optional (defined as `Optional[Budget]` in the Pydantic model), if the LLM doesn't generate budget information, this card won't be displayed. This reflects the front-end's error tolerance for data.

### 13.6.2 Loading Progress Bar

Generating a travel plan is a time-consuming operation. The back-end needs to sequentially call AttractionSearchAgent, WeatherQueryAgent, HotelAgent, and PlannerAgent, and each Agent needs to call the LLM and external APIs. The entire process may take 10-30 seconds. If the user clicks the "Start Planning" button and the page has no feedback, the user will think the system is stuck and may refresh the page or click repeatedly.

To improve user experience, we added a loading progress bar and status prompts. Currently, it's just simulated progress, but it lets users know the system is working.

```typescript
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const handleSubmit = async () => {
  loading.value = true
  loadingProgress.value = 0

  // Simulate progress updates
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = '🔍 Searching for attractions...'
      else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ Querying weather...'
      else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 Recommending hotels...'
      else loadingStatus.value = '📋 Generating itinerary...'
    }
  }, 500)

  try {
    const response = await generateTripPlan(formData.value)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '✅ Complete!'
    router.push({ name: 'result', state: { tripPlan: response } })
  } catch (error) {
    clearInterval(progressInterval)
    message.error('Failed to generate plan')
  } finally {
    loading.value = false
  }
}
```

### 13.6.3 Itinerary Editing Feature

Although AI-generated travel plans are intelligent, they may not fully meet users' personal needs. For example, users may not like a certain attraction and want to delete it, or want to adjust the order of attractions. We provide an itinerary editing feature that allows users to customize their itinerary.

The core of the editing feature is **state management**. We need to maintain two states: the current itinerary plan and the original itinerary plan. When users enter edit mode, we save a copy of the original plan. If users cancel editing, we restore the original plan. If users save changes, we update the current plan:

```typescript
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)

// Enter edit mode
const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
}
```

Note that we use `JSON.parse(JSON.stringify(...))` to deep copy the object. Why not assign directly? Because objects in JavaScript are reference types - if we assign directly, `originalPlan` and `tripPlan` will point to the same object, and modifying one will affect the other. Deep copying creates a completely independent copy.

The logic for moving attractions is to swap the positions of two elements in the array:

```typescript
// Move attraction
const moveAttraction = (dayIndex: number, attractionIndex: number, direction: 'up' | 'down') => {
  const attractions = tripPlan.value.days[dayIndex].attractions
  const newIndex = direction === 'up' ? attractionIndex - 1 : attractionIndex + 1

  if (newIndex >= 0 && newIndex < attractions.length) {
    [attractions[attractionIndex], attractions[newIndex]] =
    [attractions[newIndex], attractions[attractionIndex]]
  }
}
```

This uses ES6's destructuring assignment syntax to swap two elements. `[a, b] = [b, a]` is an elegant way to swap without needing a temporary variable.

Deleting attractions uses the array's `splice` method:

```typescript
// Delete attraction
const deleteAttraction = (dayIndex: number, attractionIndex: number) => {
  tripPlan.value.days[dayIndex].attractions.splice(attractionIndex, 1)
}
```

When saving changes, we need to reinitialize the map because attraction positions may have changed:

```typescript
// Save changes
const saveChanges = () => {
  editMode.value = false
  message.success('Changes saved')
  initMap()  // Reinitialize map
}

// Cancel editing
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = originalPlan.value
  }
  editMode.value = false
}
```

In the template, we display different UI based on the value of `editMode`. In edit mode, up, down, and delete buttons are displayed next to each attraction:

```vue
<div v-if="editMode" class="edit-buttons">
  <a-button size="small" @click="moveAttraction(dayIndex, index, 'up')">Up</a-button>
  <a-button size="small" @click="moveAttraction(dayIndex, index, 'down')">Down</a-button>
  <a-button size="small" danger @click="deleteAttraction(dayIndex, index)">Delete</a-button>
</div>
```

### 13.6.4 Export Functionality

After users generate a satisfactory travel plan, they may want to save it or share it with friends. We provide two export methods: export as image and export as PDF.

The core of the export functionality is the `html2canvas` library. This library can convert DOM elements to Canvas, and then we can export the Canvas as an image. But there's a technical challenge here: the map is rendered using Canvas, and `html2canvas` has compatibility issues when handling nested Canvas.

We tried multiple solutions, including converting the map Canvas to an image before exporting, but due to Amap's Canvas rendering mechanism and cross-origin restrictions, this solution didn't completely solve the problem. In actual projects, you may need to consider the following alternative solutions:

1. **Use Amap's static map API**: Call the `maps_staticmap` tool to generate static map images to replace dynamic maps
2. **Export separately**: Export the map and itinerary content separately, then merge them on the back-end
3. **Use screenshot service**: Use headless browsers like Puppeteer to take screenshots on the server side
4. **Simplify export content**: Hide the map when exporting, only export text content

In the current implementation, we adopted a simplified approach, temporarily hiding the map part when exporting and only exporting the text content and attraction information of the itinerary. Although this isn't the ideal solution, it ensures the export functionality is usable.

The logic for exporting as an image is simple:

```typescript
import html2canvas from 'html2canvas'

const exportAsImage = async () => {
  const element = document.getElementById('trip-plan-content')
  if (!element) return

  const canvas = await html2canvas(element, {
    backgroundColor: '#ffffff',
    scale: 2,
    useCORS: true
  })

  const link = document.createElement('a')
  link.download = `${tripPlan.value.city} Travel Plan.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
  message.success('Export successful!')
}
```

`scale: 2` means using 2x resolution, making the exported image clearer. `useCORS: true` allows cross-origin image loading, which is important for attraction images (from Unsplash).

Exporting as PDF requires additional steps: first convert to Canvas, then convert to image, and finally add to PDF:

```typescript
import jsPDF from 'jspdf'

const exportAsPDF = async () => {
  // First capture map image
  await captureMapImage()

  const element = document.getElementById('trip-plan-content')
  if (!element) return

  const canvas = await html2canvas(element, {
    backgroundColor: '#ffffff',
    scale: 2,
    useCORS: true,
    allowTaint: true
  })

  // Restore map
  restoreMap()

  const pdf = new jsPDF('p', 'mm', 'a4')
  const imgData = canvas.toDataURL('image/png')
  const imgWidth = 210  // A4 width
  const imgHeight = (canvas.height * imgWidth) / canvas.width

  pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)
  pdf.save(`${tripPlan.value.city} Travel Plan.pdf`)
  message.success('Export successful!')
}
```

Here we need to calculate the image height to maintain the aspect ratio. The width of A4 paper is 210mm, and we calculate the corresponding height based on the Canvas aspect ratio.

### 13.6.5 Side Navigation and Anchor Jumping

The Result page has a lot of content, including itinerary overview, budget details, map, daily itinerary, weather information, etc. If users want to quickly jump to a certain section, they need to scroll a long distance. We provide side navigation and anchor jumping functionality, allowing users to quickly locate.

Side navigation uses Ant Design Vue's Menu component:

```vue
<a-menu
  v-model:selectedKeys="[activeSection]"
  mode="inline"
  @click="scrollToSection"
>
  <a-menu-item key="overview">📋 Itinerary Overview</a-menu-item>
  <a-menu-item key="budget">💰 Budget Details</a-menu-item>
  <a-menu-item key="map">🗺️ Map</a-menu-item>
  <a-menu-item key="days">📅 Daily Itinerary</a-menu-item>
  <a-menu-item key="weather">🌤️ Weather</a-menu-item>
</a-menu>
```

When clicking a menu item, call the `scrollToSection` function:

```typescript
const activeSection = ref('overview')

// Scroll to specified section
const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}
```

`scrollIntoView` is a native browser API that can scroll an element into the visible area. `behavior: 'smooth'` means smooth scrolling rather than instant jumping. `block: 'start'` means the top of the element aligns with the top of the visible area.

In various parts of the page, we need to add corresponding ids:

```vue
<div id="overview">
  <!-- Itinerary overview content -->
</div>

<div id="budget">
  <!-- Budget details content -->
</div>

<div id="map">
  <!-- Map content -->
</div>
```

This way, when users click a menu item in the side navigation, the page will smoothly scroll to the corresponding section.

Through the implementation of these features, our intelligent travel assistant not only generates travel plans but also provides rich interactive features: budget calculation lets users understand costs, loading progress bar makes waiting less anxious, itinerary editing makes plans more personalized, export functionality allows plans to be shared and saved, and side navigation makes long pages easy to browse. The combination of these features forms a complete, user-friendly, and practical Web application.

## 13.7 Conclusion

Congratulations on completing Chapter 13!

Through this chapter, you not only learned how to build a complete intelligent travel assistant application, but more importantly, you mastered:

1. **System Design Thinking**: How to decompose complex problems into multiple simple tasks
2. **Engineering Practice Ability**: How to transform theoretical knowledge into runnable code
3. **Full-Stack Development Ability**: How to integrate front-end and back-end technology stacks
4. **AI Application Development**: How to use LLMs to build practical applications

This project is a starting point, not an endpoint. Based on this project, you can:

- Add more features
- Optimize user experience
- Extend to other domains (such as intelligent shopping assistant, intelligent learning assistant, etc.)
- Deploy to production environment to serve real users

The best way to learn is through practice. Don't just read the code - modify, extend, and optimize it yourself. Each practice will deepen your understanding of multi-Agent systems.

Wishing you success on your journey in AI application development!

