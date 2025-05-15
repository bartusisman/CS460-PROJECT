#!/usr/bin/env python3
import argparse
import os
import time
from dotenv import load_dotenv
from src.navigation.navigator import AppNavigator
from src.core.appium_fetcher import AppiumPageSourceFetcher
from src.utils.formatting import split_navigation_steps

# Load environment variables from .env file if present
load_dotenv()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Navigate mobile apps using LLM and Appium')
    
    # Platform selection
    parser.add_argument('--platform', type=str, required=True, choices=['android', 'ios'],
                        help='Mobile platform (android or ios)')
    
    # Platform-specific options
    parser.add_argument('--device-name', type=str, required=True,
                        help='Device name (e.g., "iPhone 16 Pro")')
    parser.add_argument('--platform-version', type=str,
                        help='Platform version (e.g., "18.2" for iOS)')
    parser.add_argument('--bundle-id', type=str,
                        help='Bundle ID for iOS app (e.g., "com.pediatricstechnologies.app")')
    parser.add_argument('--app-package', type=str, 
                        help='Android app package (e.g., com.example.app)')
    parser.add_argument('--app-activity', type=str,
                        help='Android app activity (e.g., com.example.app.MainActivity)')
    parser.add_argument('--app-path', type=str,
                        help='Path to app file (.apk or .ipa)')
    
    # OpenAI configuration
    parser.add_argument('--api-key', type=str,
                        help='OpenAI API key (can also use OPENAI_API_KEY env var)')
    parser.add_argument('--model', type=str, default='gpt-4.1-mini',
                        help='OpenAI model name (default: gpt-4.1-mini)')
    
    # Navigation
    parser.add_argument('instruction', type=str, nargs='?',
                        help='Navigation instruction (e.g., "Click login button")')
    
    # Run modes
    parser.add_argument('--interactive', action='store_true',
                        help='Run in interactive mode to navigate continuously')
    parser.add_argument('--debug', action='store_true',
                        help='Show detailed debug information')
    parser.add_argument('--screenshots', action='store_true',
                        help='Save screenshots during navigation')
    
    return parser.parse_args()

def save_screenshot(fetcher, filename='screenshot.png'):
    """Save a screenshot if the driver is available"""
    try:
        if fetcher and fetcher.driver:
            # Create screenshots directory if it doesn't exist
            os.makedirs('screenshots', exist_ok=True)
            filepath = os.path.join('screenshots', filename)
            fetcher.driver.get_screenshot_as_file(filepath)
            print(f"Screenshot saved as {filepath}")
            return True
    except Exception as e:
        print(f"Failed to save screenshot: {e}")
    return False

def main():
    args = parse_arguments()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key must be provided via --api-key or OPENAI_API_KEY environment variable")
        return 1
    
    # Create navigator
    navigator = AppNavigator(api_key=api_key, model_name=args.model)
    
    # Enable debug mode if requested
    if args.debug:
        navigator.set_debug(True)
    
    # Connect to app
    print(f"Connecting to Appium...")
    
    connected = False
    # Set platform-specific capabilities
    if args.platform.lower() == 'ios':
        # Create fetcher with iOS settings
        fetcher = AppiumPageSourceFetcher(platform=args.platform, device_name=args.device_name)
        
        # Set platform version if specified
        if args.platform_version:
            fetcher.set_platform_version(args.platform_version)
            
        # For already installed apps
        if args.bundle_id:
            fetcher.capabilities['bundleId'] = args.bundle_id
            
        # Set app path if provided
        fetcher.set_app(app_path=args.app_path)
        
        # Connect to Appium
        connected = fetcher.connect()
        
        # Use the connected fetcher in our navigator
        if connected:
            navigator.fetcher = fetcher
            navigator.session_manager.set_driver(fetcher.driver)
            from src.elements.element_finder import ElementFinder
            from src.pickers.picker_handler import PickerHandler
            navigator.element_finder = ElementFinder(fetcher.driver)
            navigator.picker_handler = PickerHandler(
                fetcher.driver, 
                element_finder=navigator.element_finder,
                session_manager=navigator.session_manager
            )
    else:
        # Android connect
        connected = navigator.connect_to_app(
            platform=args.platform,
            app_package=args.app_package,
            app_activity=args.app_activity,
            app_path=args.app_path
        )
    
    if not connected:
        print("Failed to connect to app. Make sure Appium server is running and app capabilities are correct.")
        return 1
    
    print("Connected to app successfully!")
    
    # Take initial screenshot if requested
    if args.screenshots:
        save_screenshot(navigator.fetcher, "initial_screen.png")
    
    try:
        if args.interactive:
            # Interactive mode
            print("\nInteractive navigation mode. Type 'exit' to quit.")
            print("Type 'screenshot' to take a screenshot.")
            
            command_count = 0
            
            while True:
                instruction = input("\nWhat would you like to do? > ")
                if instruction.lower() in ('exit', 'quit'):
                    break
                
                # Special command to take a screenshot
                if instruction.lower() in ('screenshot', 'screen'):
                    save_screenshot(navigator.fetcher, f"manual_{command_count}.png")
                    continue
                
                print(f"Navigating: {instruction}")
                
                # Take screenshot before action if requested
                if args.screenshots:
                    save_screenshot(navigator.fetcher, f"before_{command_count}.png")
                
                # Check if instruction contains multiple steps
                steps = split_navigation_steps(instruction)
                if len(steps) > 1:
                    result = navigator.navigate_multi_step(instruction)
                else:
                    result = navigator.navigate(instruction)
                
                print(f"Result: {result}")
                
                # Take screenshot after action if requested
                if args.screenshots:
                    save_screenshot(navigator.fetcher, f"after_{command_count}.png")
                
                command_count += 1
                
        elif args.instruction:
            # Single instruction mode
            print(f"Navigating: {args.instruction}")
            
            # Take screenshot before action if requested
            if args.screenshots:
                save_screenshot(navigator.fetcher, "before.png")
            
            # Check if instruction contains multiple steps
            steps = split_navigation_steps(args.instruction)
            if len(steps) > 1:
                result = navigator.navigate_multi_step(args.instruction)
            else:
                result = navigator.navigate(args.instruction)
            
            print(f"Result: {result}")
            
            # Take screenshot after action if requested
            if args.screenshots:
                save_screenshot(navigator.fetcher, "after.png")
        else:
            print("No instruction provided. Use --interactive mode or provide an instruction.")
    
    finally:
        # Always close the connection when done
        print("Closing connection...")
        navigator.close()
    
    return 0

if __name__ == "__main__":
    exit(main()) 