# LLM-Powered App Navigator

This project uses LangChain, Appium, and GPT models to create an AI-powered navigator for mobile applications. It can interpret natural language instructions, analyze UI elements, and perform navigation actions automatically.

## Architecture Overview

The system consists of three main components:

1. **Appium Interface** (`appium_page_source.py`): Manages connection to mobile devices/emulators and extracts UI information.
2. **LLM Navigation Engine** (`langchain_appium_navigator.py`): Uses LLMs to understand user instructions and determine appropriate UI interactions.
3. **Command Line Interface** (`app_navigator_cli.py`): Provides a user-friendly interface to control the navigation.

## Component Details

### appium_page_source.py

This component serves as the interface between our navigator and the mobile device:

- Creates and maintains Appium sessions
- Extracts XML page source from mobile apps
- Handles platform-specific capabilities for iOS and Android
- Implements session tracking and health checks
- Provides screenshot capabilities
- Supports real devices and simulators/emulators

### langchain_appium_navigator.py

The brain of the system that uses LLMs to understand app navigation:

- Integrates with OpenAI's GPT models via LangChain
- Analyzes UI element structure to identify interactive components
- Matches user instructions to appropriate UI elements
- Executes navigation actions (clicks, input, swipes)
- Implements multi-step navigation by breaking complex instructions into sequential steps
- Provides comprehensive element discovery algorithms to find UI elements across different platforms
- Uses retry mechanisms and error handling for robust navigation

### app_navigator_cli.py

The user interface that ties everything together:

- Provides a command-line interface for controlling the navigator
- Supports interactive mode for continuous navigation
- Enables multi-step navigation processing
- Implements debugging features like screenshots and element listing
- Handles platform-specific arguments for iOS and Android
- Supports various OpenAI models with configurable settings

## How It Works

1. **Connection**: The system connects to a mobile device or emulator via Appium
2. **UI Analysis**: When a navigation command is received, it captures the current screen's XML source
3. **Element Discovery**: It identifies all interactive elements on the screen (buttons, links, text fields, etc.)
4. **LLM Processing**: The user's instruction is sent to an LLM along with the UI structure
5. **Navigation Decision**: The LLM determines which element to interact with and how
6. **Action Execution**: The system performs the selected action (click, input text, etc.)
7. **Multi-step Processing**: For complex instructions, the process repeats for each step

## Usage Examples

### Basic Usage

```python
from langchain_appium_navigator import AppNavigator

# Create a navigator instance
navigator = AppNavigator(api_key="your_openai_api_key_here")

# Connect to your app
navigator.connect_to_app(
    platform='ios',
    device_name='iPhone 16 Pro',
    platform_version='18.2',
    bundle_id='com.apple.Preferences'
)

# Navigate using natural language
result = navigator.navigate("Open WiFi settings")

# For multi-step navigation
results = navigator.navigate_multi_step("Go to Privacy then tap Location Services")

# Close when done
navigator.close()
```

### Command Line Interface

```bash
# Simple navigation
python app_navigator_cli.py --platform ios --device-name "iPhone 16 Pro" --platform-version "18.2" --bundle-id "com.apple.Preferences" "Open WiFi settings"

# Interactive mode with multi-step support
python3 app_navigator_cli.py --platform ios --device-name "iPhone 16 Pro" --platform-version "18.2" --bundle-id "com.apple.Preferences" --interactive --debug
```

## Special Features

- **Multi-step Navigation**: Process complex instructions like "go to settings then tap wifi"
- **Element Discovery**: Use the "show" command to see all available UI elements
- **Screenshots**: Capture screenshots during navigation for debugging
- **Model Selection**: Choose different OpenAI models based on needs and budget
- **Session Management**: Manual session management with detailed error feedback
- **Real Device Support**: Connect to real iOS devices with UDID

## Prerequisites

- Python 3.7+
- Appium server set up and running
- Android or iOS emulator/device connected
- OpenAI API key

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Set up your environment variables by creating a `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## LLM Usage

The navigator can use various OpenAI models:

- **GPT-4.1 Mini** (default): Good balance of performance and cost
- **GPT-3.5 Turbo**: More cost-effective for simpler apps
- **GPT-3.5 Turbo Instruct**: Most economical option

The model analyzes the UI structure and user instructions to determine the most appropriate element to interact with. It excels at:

1. Understanding natural language navigation requests
2. Matching requests to appropriate UI elements
3. Finding alternative paths when exact matches aren't available
4. Breaking down complex instructions into sequential steps

## License

MIT
