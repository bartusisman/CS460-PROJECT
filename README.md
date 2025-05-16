# LangChain Appium Navigator

A modular mobile app navigation tool that uses LLMs to intelligently navigate mobile applications through natural language instructions.

## Overview

This library integrates:

- LangChain and LLMs for understanding natural language commands
- Appium for mobile device automation
- Specialized components for element finding, date/time pickers, and UI navigation

## Project Structure

The project has been modularized into the following structure:

```
src/
├── core/              # Core functionality
│   ├── appium_fetcher.py    # Appium connection handling
│   └── session_manager.py   # Session state management
├── elements/          # UI element handling
│   ├── element_finder.py    # Element finding strategies
│   └── element_parser.py    # XML parsing and element extraction
├── navigation/        # Navigation logic
│   └── navigator.py         # Main navigation controller
├── pickers/           # Date/time picker handling
│   └── picker_handler.py    # Specialized code for date/time pickers
└── utils/             # Utility functions
    └── formatting.py        # String formatting and processing

app_navigator_cli.py   # Command-line interface
```

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure you have Appium server installed and running:

   ```bash
   npm install -g appium
   appium
   ```

3. Set your OpenAI API key in the environment variables or as a parameter:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```
   Alternatively, create a `.env` file in the project root with:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

## Usage

### Command Line Interface

#### For Android:

```bash
# Interactive navigation mode (Android)
python3 app_navigator_cli.py --platform android --app-package com.example.app --app-activity com.example.app.MainActivity --interactive

# Single command navigation (Android)
python3 app_navigator_cli.py --platform android --app-package com.example.app --app-activity com.example.app.MainActivity "click on login button"

# To install and navigate a specific APK file
python3 app_navigator_cli.py --platform android --app-path /path/to/your/app.apk --interactive
```

#### For iOS:

```bash
# Interactive mode for iOS simulator
python3 app_navigator_cli.py --platform ios --device-name "iPhone 13" --platform-version 15.0 --bundle-id com.example.app --interactive

# For iOS real device
python3 app_navigator_cli.py --platform ios --device-name "Your iPhone" --udid YOUR-DEVICE-UDID --bundle-id com.example.app --interactive
```

#### Advanced Options:

```bash
# With screenshot capturing enabled
python app_navigator_cli.py --platform android --app-package com.example.app --app-activity com.example.app.MainActivity --screenshots --interactive

# With debug mode for verbose output
python app_navigator_cli.py --platform android --app-package com.example.app --app-activity com.example.app.MainActivity --debug --interactive

# Using a specific OpenAI model
python app_navigator_cli.py --platform android --app-package com.example.app --app-activity com.example.app.MainActivity --model gpt-4.1-mini --interactive
```

#### Multi-step navigation examples:

```bash
# Execute multiple navigation steps in one command
python app_navigator_cli.py --platform android --app-package com.example.app --app-activity com.example.app.MainActivity "click login then enter username testuser then enter password testpass then click submit"
```

### Core Modules

#### AppNavigator

The main class that coordinates navigation:

```python
from src.navigation.navigator import AppNavigator

# Initialize with OpenAI API key
navigator = AppNavigator(api_key="your-api-key", model_name="gpt-4.1-mini")

# Connect to app
navigator.connect_to_app(
    platform='android',
    app_package='com.example.app',
    app_activity='com.example.app.MainActivity'
)

# Simple navigation
result = navigator.navigate("click on the login button")

# Multi-step navigation
results = navigator.navigate_multi_step("tap the login button then enter username admin then tap login")

# Cleanup when done
navigator.close()
```

#### Element Finding

```python
from src.elements.element_finder import ElementFinder

# Requires an Appium driver instance
finder = ElementFinder(driver)

# Find an element by text, content-desc, or other attributes
element = finder.find_element("Login")

# Click the element
if element:
    element.click()
```

#### Picker Handling

```python
from src.pickers.picker_handler import PickerHandler

# Create picker handler
picker = PickerHandler(driver)

# Handle date picker
picker.handle_scroll_picker("Date", "15 April 2024")

# Handle time picker
picker.handle_scroll_picker("Time", "14:30")

# Confirm picker selection
picker.confirm_picker()
```

## Features

- **Natural Language Navigation**: Navigate apps using simple instructions
- **Multi-Step Commands**: Chain multiple actions like "click login, enter username then tap submit"
- **Smart Element Finding**: Uses multiple strategies to find the right elements
- **Date & Time Pickers**: Special handling for complex date and time selection
- **Platform Agnostic**: Works with both Android and iOS
- **Interactive Mode**: Interactive CLI for navigation experiments


## How to Use
for multiple actions add then, and keywords between actions
for picking something in scrollview say pick ...
for clicking say click 

## License

[Your license information]
