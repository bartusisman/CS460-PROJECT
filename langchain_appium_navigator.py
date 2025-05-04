from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os
import json
import xml.etree.ElementTree as ET
from appium_page_source import AppiumPageSourceFetcher
from appium.webdriver.common.mobileby import MobileBy
import time
import re

class AppNavigator:
    def __init__(self, api_key=None, model_name="gpt-4.1-mini"):
        """
        Initialize the AppNavigator with OpenAI API key and model
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY environment variable)
            model_name: Name of the LLM model to use
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Use ChatOpenAI for GPT-4.1 mini
        self.llm = ChatOpenAI(temperature=0, model_name=model_name)
        self.fetcher = AppiumPageSourceFetcher()
        
        # Create improved prompt template for navigation with better iOS specific guidance
        self.prompt_template = PromptTemplate(
            input_variables=["page_source", "user_instruction", "available_elements"],
            template="""
            You are an AI assistant that helps navigate mobile applications, specifically iOS apps.
            
            Below is the XML page source of the current iOS app screen:
            {page_source}
            
            Here are the identifiable interactive elements on the current screen:
            {available_elements}
            
            The user wants to: {user_instruction}
            
            Your task is to identify the MOST APPROPRIATE element from the available elements list above that should be interacted with to fulfill the user's request.
            
            DO NOT suggest clicking elements that don't match the user's request. For example:
            - If user asks for WiFi settings, look for elements with "Wi-Fi", "WiFi", or "Network"
            - If user asks for Bluetooth, look for "Bluetooth" elements
            - If user asks for General, look for "General" elements
            
            Be precise and choose the element that directly relates to the request. Do not select unrelated elements like "Apple Account" for specific settings. Choose the option that most directly matches what the user is looking for.
            
            Return a JSON response with the following format:
            {{
                "element_type": "The element type (e.g., XCUIElementTypeButton, XCUIElementTypeCell, etc.)",
                "action": "click",
                "identifier": "The exact name, label, or ID of the element from the available elements list",
                "explanation": "Brief explanation of why this element was chosen",
                "input_value": null
            }}
            
            Only include input_value if the action is "input".
            """
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        
        # Add retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # Debug flag
        self.debug_mode = False
    
    def set_debug(self, debug_mode=True):
        """Enable or disable debug mode"""
        self.debug_mode = debug_mode
    
    def connect_to_app(self, platform='android', app_package=None, app_activity=None, app_path=None):
        """Connect to the mobile app using Appium"""
        self.fetcher = AppiumPageSourceFetcher(platform=platform)
        self.fetcher.set_app(
            app_path=app_path,
            app_package=app_package,
            app_activity=app_activity
        )
        return self.fetcher.connect()
    
    def _extract_available_elements(self, page_source):
        """Extract a list of available interactive elements from the page source"""
        try:
            available_elements = []
            root = ET.fromstring(page_source)
            
            # Define interactive element types we're interested in
            interactive_types = [
                'XCUIElementTypeButton', 
                'XCUIElementTypeCell', 
                'XCUIElementTypeTextField',
                'XCUIElementTypeSwitch',
                'XCUIElementTypeLink',
                'XCUIElementTypeSearchField',
                'XCUIElementTypeTable',
                'XCUIElementTypeStaticText'  # Include text elements as they might be clickable in iOS
            ]
            
            # Find all elements of interactive types
            for elem_type in interactive_types:
                # Find all elements of this type
                xpath = f".//*[@type='{elem_type}']"
                elements = root.findall(xpath)
                
                for elem in elements:
                    # Get element attributes
                    attrs = {
                        'type': elem.get('type', ''),
                        'name': elem.get('name', ''),
                        'label': elem.get('label', ''),
                        'value': elem.get('value', ''),
                        'enabled': elem.get('enabled', 'false'),
                        'visible': elem.get('visible', 'false')
                    }
                    
                    # Skip disabled or invisible elements
                    if attrs['enabled'] != 'true' or attrs['visible'] != 'true':
                        continue
                    
                    # Get the best identifier (name, label, or value)
                    identifier = attrs['name'] or attrs['label'] or attrs['value']
                    if identifier:
                        # Remove duplicates and add to list
                        element_info = f"{attrs['type']}: {identifier}"
                        if element_info not in available_elements:
                            available_elements.append(element_info)
            
            # Format the list for display
            if available_elements:
                return "\n".join(available_elements)
            else:
                return "No identifiable interactive elements found on screen."
                
        except Exception as e:
            print(f"Error extracting elements: {str(e)}")
            return "Error extracting elements from page source."
    
    def _split_navigation_steps(self, instruction):
        """Split a multi-step navigation instruction into individual steps"""
        # Common separation indicators
        separators = [
            " then ", " and then ", " after that ", " next ",
            ", then ", ", and then ", ", after that ", ", next ",
            "; then ", "; and then ", "; after that ", "; next "
        ]
        
        # Split by each separator
        steps = [instruction]
        for separator in separators:
            new_steps = []
            for step in steps:
                new_steps.extend(step.split(separator))
            steps = new_steps
        
        # Filter out empty steps and strip leading/trailing whitespace
        steps = [step.strip() for step in steps if step.strip()]
        
        # If no steps were found or no separators detected, return the original instruction
        if not steps:
            return [instruction]
        
        return steps
    
    def navigate_multi_step(self, instruction):
        """
        Navigate through multiple steps in a single instruction
        
        Args:
            instruction: User instruction that may contain multiple steps
        """
        steps = self._split_navigation_steps(instruction)
        
        if len(steps) > 1:
            print(f"Detected {len(steps)} navigation steps:")
            for i, step in enumerate(steps):
                print(f"  Step {i+1}: {step}")
        
        results = []
        
        # Process each step sequentially
        for i, step in enumerate(steps):
            print(f"\nExecuting step {i+1}/{len(steps)}: {step}")
            result = self.navigate(step)
            results.append(result)
            
            # Wait between steps
            if i < len(steps) - 1:
                time.sleep(2)  # Give UI time to update between steps
        
        return results
    
    def navigate(self, instruction):
        """
        Navigate in the app based on user instruction
        
        Args:
            instruction: User instruction (e.g., "Click on the login button")
        """
        # Get the current page source
        page_source = self.fetcher.get_page_source()
        if not page_source:
            return {"error": "Failed to get page source"}
        
        # Extract available elements for better navigation
        available_elements = self._extract_available_elements(page_source)
        
        if self.debug_mode:
            print("\nAvailable interactive elements on screen:")
            print(available_elements)
        
        # Format page source (truncate if too large)
        formatted_source = self._format_page_source(page_source)
        
        # Get LLM recommendation for navigation
        response = self.chain.run(
            page_source=formatted_source, 
            user_instruction=instruction,
            available_elements=available_elements
        )
        
        try:
            # Parse the JSON response
            action_data = json.loads(response)
            
            # Log what we're going to do
            print(f"Selected element: {action_data.get('identifier', 'Unknown')} ({action_data.get('element_type', 'Unknown')})")
            print(f"Action: {action_data.get('action', 'Unknown')}")
            
            # Execute the recommended action
            action_result = self._execute_action(action_data)
            
            # Merge any error messages from action execution
            if isinstance(action_result, dict) and "error" in action_result:
                action_data["error"] = action_result["error"]
            
            return action_data
        except json.JSONDecodeError:
            return {"error": f"Failed to parse LLM response as JSON: {response}"}
        except Exception as e:
            return {"error": f"Failed to execute action: {str(e)}"}
    
    def _format_page_source(self, page_source, max_length=8000):
        """Format and truncate page source if needed"""
        if len(page_source) > max_length:
            # Simple truncation, could be improved with more intelligent parsing
            return page_source[:max_length] + "... (truncated)"
        return page_source
    
    def _execute_action(self, action_data):
        """Execute the action recommended by the LLM"""
        if not self.fetcher.check_session():
            return {"error": "Failed to establish a valid Appium session"}
        
        element_type = action_data.get("element_type", "")
        action = action_data.get("action", "")
        identifier = action_data.get("identifier", "")
        input_value = action_data.get("input_value")
        
        # Find the element with retries
        for attempt in range(self.max_retries):
            try:
                # Find the element
                element = self._find_element(identifier)
                
                if not element:
                    if attempt < self.max_retries - 1:
                        print(f"Element '{identifier}' not found, retrying ({attempt+1}/{self.max_retries})...")
                        time.sleep(self.retry_delay)
                        # Refresh session before retry
                        self.fetcher.check_session()
                        continue
                    else:
                        return {"error": f"Element with identifier '{identifier}' not found after {self.max_retries} attempts"}
                
                # Perform the action
                if action == "click":
                    element.click()
                elif action == "input" and input_value:
                    element.clear()
                    element.send_keys(input_value)
                elif action == "swipe":
                    # This is a simplified implementation
                    self.fetcher.driver.swipe(element.location['x'], element.location['y'], 
                                             element.location['x'], element.location['y'] - 200, 500)
                
                # Short pause after action to let UI respond
                time.sleep(1)
                return {"success": True}
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"Action failed, retrying ({attempt+1}/{self.max_retries}): {str(e)}")
                    time.sleep(self.retry_delay)
                    # Refresh session before retry
                    self.fetcher.check_session()
                else:
                    return {"error": f"Failed to execute action after {self.max_retries} attempts: {str(e)}"}
    
    def _find_element(self, identifier):
        """Find an element using various strategies"""
        if not self.fetcher.driver:
            print("Driver not initialized")
            return None
        
        # Add stability - wait a moment before looking for elements
        time.sleep(0.5)
        
        # Clean up identifier if it contains type information
        if ":" in identifier:
            # Format might be "XCUIElementTypeButton: Settings"
            clean_identifier = identifier.split(":", 1)[1].strip()
        else:
            clean_identifier = identifier.strip()
        
        # Log what we're looking for
        print(f"Finding element with identifier: '{clean_identifier}'")
        
        strategies = [
            # Try by ID
            lambda: self.fetcher.driver.find_element(MobileBy.ID, clean_identifier),
            
            # Try by text (Android)
            lambda: self.fetcher.driver.find_element(MobileBy.ANDROID_UIAUTOMATOR, 
                                                 f'new UiSelector().text("{clean_identifier}")') 
                if self.fetcher.platform == 'android' else None,
            
            # Try by content description (accessibility ID)
            lambda: self.fetcher.driver.find_element(MobileBy.ACCESSIBILITY_ID, clean_identifier),
            
            # Try by name (iOS)
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//*[@name='{clean_identifier}']"),
            
            # Try by label (iOS)
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//*[@label='{clean_identifier}']"),
            
            # Try by value (iOS)
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//*[@value='{clean_identifier}']"),
            
            # Try by text content in iOS
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//XCUIElementTypeStaticText[@value='{clean_identifier}']"),
            
            # Try by partial text match in iOS name attribute
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//*[contains(@name, '{clean_identifier}')]"),
            
            # Try by partial text match in iOS label attribute
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//*[contains(@label, '{clean_identifier}')]"),
                                                 
            # Try by partial text match in iOS value attribute
            lambda: self.fetcher.driver.find_element(MobileBy.XPATH, 
                                                 f"//*[contains(@value, '{clean_identifier}')]"),
        ]
        
        for strategy in strategies:
            try:
                element = strategy()
                if element:
                    return element
            except:
                continue
        
        return None
    
    def close(self):
        """Close the Appium connection"""
        if self.fetcher:
            self.fetcher.disconnect()


if __name__ == "__main__":
    # Example usage
    navigator = AppNavigator(api_key="your_openai_api_key_here")  # Replace with your OpenAI API key
    
    # Connect to app
    navigator.connect_to_app(
        platform='android',
        app_package='com.example.app',  # Replace with your app package
        app_activity='com.example.app.MainActivity'  # Replace with your app activity
    )
    
    # Navigate based on user instruction
    result = navigator.navigate("Login with username 'testuser' and password 'password123'")
    print(f"Navigation result: {result}")
    
    # Close the connection
    navigator.close() 