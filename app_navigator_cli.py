#!/usr/bin/env python3
import argparse
import os
from dotenv import load_dotenv
from langchain_appium_navigator import AppNavigator

# Load environment variables from .env file if present
load_dotenv()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Navigate mobile apps using LLM and Appium')
    
    # Platform selection
    parser.add_argument('--platform', type=str, default='android', choices=['android', 'ios'],
                        help='Mobile platform (android or ios)')
    
    # Android-specific options
    android_group = parser.add_argument_group('Android Options')
    android_group.add_argument('--app-package', type=str, 
                        help='Android app package (e.g., com.example.app)')
    android_group.add_argument('--app-activity', type=str,
                        help='Android app activity (e.g., com.example.app.MainActivity)')
    
    # iOS-specific options
    ios_group = parser.add_argument_group('iOS Options')
    ios_group.add_argument('--platform-version', type=str,
                       help='iOS platform version (e.g., 15.0)')
    ios_group.add_argument('--device-name', type=str,
                       help='Device name (e.g., "iPhone 13")')
    ios_group.add_argument('--udid', type=str,
                       help='UDID for real iOS devices')
    ios_group.add_argument('--bundle-id', type=str,
                       help='Bundle ID for an already installed iOS app (e.g., "com.apple.Preferences" for Settings)')
    
    # Common options
    parser.add_argument('--app-path', type=str,
                        help='Path to app file (.apk or .ipa)')
    
    # Appium configuration
    parser.add_argument('--appium-url', type=str, default='http://localhost:4723',
                        help='Appium server URL')
    
    # OpenAI configuration
    parser.add_argument('--api-key', type=str,
                        help='OpenAI API key (can also use OPENAI_API_KEY env var)')
    parser.add_argument('--model', type=str, default='gpt-4.1-mini',
                        help='OpenAI model name (default: gpt-4.1-mini)')
    
    # Navigation
    parser.add_argument('instruction', type=str, nargs='?',
                        help='Navigation instruction (e.g., "Click login button")')
    
    # Interactive mode
    parser.add_argument('--interactive', action='store_true',
                        help='Run in interactive mode to navigate continuously')
    
    # Debug mode
    parser.add_argument('--debug', action='store_true',
                        help='Show full page source and detailed errors')
    
    # Screenshots
    parser.add_argument('--screenshots', action='store_true',
                        help='Save screenshots during navigation')
    
    # Multi-step mode
    parser.add_argument('--no-multi-step', action='store_true',
                        help='Disable automatic multi-step processing')
    
    return parser.parse_args()

def save_screenshot(fetcher, filename='screenshot.png'):
    """Save a screenshot if the driver is available"""
    try:
        if fetcher and fetcher.driver:
            fetcher.driver.get_screenshot_as_file(filename)
            print(f"Screenshot saved as {filename}")
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
    
    # Set up platform specifics for Appium
    if args.platform:
        print(f"Configuring for {args.platform.upper()} platform...")
        
    # Connect to app
    print(f"Connecting to Appium...")
    
    from appium_page_source import AppiumPageSourceFetcher
    
    # Initialize the fetcher with platform settings
    fetcher = AppiumPageSourceFetcher(platform=args.platform, device_name=args.device_name)
    
    # Set platform version if specified
    if args.platform_version:
        fetcher.set_platform_version(args.platform_version)
    
    # Set iOS-specific capabilities
    if args.platform.lower() == 'ios':
        # For real devices
        if args.udid:
            fetcher.capabilities['udid'] = args.udid
            fetcher.capabilities['xcodeOrgId'] = os.environ.get('XCODE_ORG_ID', '')
            fetcher.capabilities['xcodeSigningId'] = os.environ.get('XCODE_SIGNING_ID', 'iPhone Developer')
            # Real devices need the real device flag
            fetcher.capabilities['realDevice'] = True
        
        # For already installed apps (like Settings)
        if args.bundle_id:
            fetcher.capabilities['bundleId'] = args.bundle_id
    
    # Set app details
    fetcher.set_app(
        app_path=args.app_path,
        app_package=args.app_package,
        app_activity=args.app_activity
    )
    
    # Connect to Appium server
    connected = fetcher.connect(appium_url=args.appium_url)
    
    if not connected:
        print("Failed to connect to app. Make sure Appium server is running and app capabilities are correct.")
        
        if args.debug:
            print("\nDebug info:")
            print(f"Platform: {args.platform}")
            print(f"App path: {args.app_path}")
            print(f"App package: {args.app_package}")
            print(f"App activity: {args.app_activity}")
            print(f"Device name: {args.device_name}")
            print(f"Platform version: {args.platform_version}")
            print(f"Bundle ID: {args.bundle_id}")
            print(f"UDID: {args.udid}")
            print(f"Appium URL: {args.appium_url}")
            print(f"Capabilities: {fetcher.capabilities}")
        
        return 1
    
    # Use the connected fetcher in our navigator
    navigator.fetcher = fetcher
    
    print("Connected to app successfully!")
    
    # Take initial screenshot if requested
    if args.screenshots:
        save_screenshot(fetcher, "initial_screen.png")
    
    # Determine if we should use multi-step navigation
    use_multi_step = not args.no_multi_step
    
    try:
        if args.interactive:
            # Interactive mode
            print("\nInteractive navigation mode. Type 'exit' to quit.")
            if use_multi_step:
                print("Multi-step navigation is ENABLED. Use commands like 'go to settings then tap wifi'")
            else:
                print("Multi-step navigation is DISABLED. Use single commands only.")
            
            command_count = 0
            
            while True:
                instruction = input("\nWhat would you like to do? > ")
                if instruction.lower() in ('exit', 'quit'):
                    break
                
                # Special command to list all elements on screen
                if instruction.lower() in ('list', 'elements', 'show'):
                    page_source = fetcher.get_page_source()
                    elements = navigator._extract_available_elements(page_source)
                    print("\nAvailable elements on screen:")
                    print(elements)
                    continue
                
                # Special command to take a screenshot
                if instruction.lower() in ('screenshot', 'screen'):
                    save_screenshot(fetcher, f"screenshot_{command_count}.png")
                    continue
                
                # Special command to toggle multi-step mode
                if instruction.lower() in ('toggle multi', 'toggle multi-step'):
                    use_multi_step = not use_multi_step
                    print(f"Multi-step navigation is now {'ENABLED' if use_multi_step else 'DISABLED'}")
                    continue
                    
                print(f"Navigating: {instruction}")
                
                # Take screenshot before action if requested
                if args.screenshots:
                    save_screenshot(fetcher, f"before_{command_count}.png")
                
                # Determine whether to use multi-step navigation
                if use_multi_step:
                    # Check if instruction contains multiple steps
                    steps = navigator._split_navigation_steps(instruction)
                    if len(steps) > 1:
                        result = navigator.navigate_multi_step(instruction)
                    else:
                        result = navigator.navigate(instruction)
                else:
                    # Use single-step navigation
                    result = navigator.navigate(instruction)
                
                print(f"Result: {result}")
                
                # Take screenshot after action if requested
                if args.screenshots:
                    save_screenshot(fetcher, f"after_{command_count}.png")
                
                command_count += 1
                
        elif args.instruction:
            # Single instruction mode
            print(f"Navigating: {args.instruction}")
            
            # Take screenshot before action if requested
            if args.screenshots:
                save_screenshot(fetcher, "before.png")
            
            # Determine whether to use multi-step navigation
            if use_multi_step:
                # Check if instruction contains multiple steps
                steps = navigator._split_navigation_steps(args.instruction)
                if len(steps) > 1:
                    result = navigator.navigate_multi_step(args.instruction)
                else:
                    result = navigator.navigate(args.instruction)
            else:
                # Use single-step navigation
                result = navigator.navigate(args.instruction)
            
            print(f"Result: {result}")
            
            # Take screenshot after action if requested
            if args.screenshots:
                save_screenshot(fetcher, "after.png")
                
        else:
            print("No instruction provided. Use --interactive or provide an instruction argument.")
    finally:
        # Clean up
        print("Closing connection...")
        navigator.close()
    
    return 0

if __name__ == "__main__":
    exit(main()) 