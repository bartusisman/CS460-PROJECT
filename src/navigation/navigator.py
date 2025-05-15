from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os
import json
import time
import re

from src.core.session_manager import SessionManager
from src.elements.element_parser import extract_available_elements, detect_popup_state
from src.elements.element_finder import ElementFinder
from src.utils.formatting import format_page_source, split_navigation_steps
from src.pickers.picker_handler import PickerHandler

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
        
        # Use ChatOpenAI for GPT models
        self.llm = ChatOpenAI(temperature=0, model_name=model_name)
        
        # Create improved prompt template for navigation with better app-agnostic guidance
        self.prompt_template = PromptTemplate(
            input_variables=["page_source", "user_instruction", "available_elements"],
            template="""
            You are an AI assistant that helps navigate mobile applications.
            
            Below is the XML page source of the current mobile app screen:
            {page_source}
            
            Here are the identifiable interactive elements on the current screen:
            {available_elements}
            
            The user wants to: {user_instruction}
            
            Your task is to identify the MOST APPROPRIATE element from the available elements list above that should be interacted with to fulfill the user's request.
            
            DO NOT suggest clicking elements that don't match the user's request. Choose the element that directly relates to the request.
            
            IMPORTANT: If the user is asking to select a specific TIME or DATE value:
            
            1. For DATE pickers (like "select April 12, 2024" or "pick May 14, 2025"):
               - Use action "scroll_picker"
               - Include the target date value as "DAY MONTH YEAR" (e.g., "12 April 2024") in input_value
               - Set identifier to the picker element (any date/picker-related element if visible)
            
            2. For TIME pickers (like "pick 21:05" or "select 20:58"):
               - Use action "scroll_picker" 
               - Include the target time value in input_value field
               - Set identifier to "Time" (or similar time-related element if visible)
            
            3. For confirming any picker selection (date or time):
               - Use action "click" with the "Confirm" or "Done" button as the identifier
            
            Return a JSON response with the following format:
            {{
                "element_type": "The element type (e.g., XCUIElementTypeButton, android.widget.Button, etc.)",
                "action": "click",
                "identifier": "The exact name, label, or ID of the element from the available elements list",
                "explanation": "Brief explanation of why this element was chosen",
                "input_value": null
            }}
            
            Only include input_value if the action is "input" or "scroll_picker".
            """
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        
        # Initialize helper modules with None values (to be set later)
        self.fetcher = None
        self.session_manager = SessionManager()
        self.element_finder = None
        self.picker_handler = None
        
        # Debug flag
        self.debug_mode = False
    
    def set_debug(self, debug_mode=True):
        """Enable or disable debug mode"""
        self.debug_mode = debug_mode
    
    def connect_to_app(self, platform='android', app_package=None, app_activity=None, app_path=None):
        """Connect to the mobile app using Appium"""
        # Import here to avoid circular imports
        from src.core.appium_fetcher import AppiumPageSourceFetcher
        
        self.fetcher = AppiumPageSourceFetcher(platform=platform)
        self.fetcher.set_app(
            app_path=app_path,
            app_package=app_package,
            app_activity=app_activity
        )
        
        # If connection is successful, initialize other components
        if self.fetcher.connect():
            self.session_manager.set_driver(self.fetcher.driver)
            self.element_finder = ElementFinder(self.fetcher.driver)
            self.picker_handler = PickerHandler(
                self.fetcher.driver, 
                element_finder=self.element_finder,
                session_manager=self.session_manager
            )
            return True
        
        return False
    
    def navigate_multi_step(self, instruction):
        """
        Navigate through multiple steps in a single instruction
        
        Args:
            instruction: User instruction that may contain multiple steps
        """
        steps = split_navigation_steps(instruction)
        
        if len(steps) > 1:
            print(f"Detected {len(steps)} navigation steps:")
            for i, step in enumerate(steps):
                print(f"  Step {i+1}: {step}")
        
        results = []
        
        # Process each step sequentially
        for i, step in enumerate(steps):
            print(f"\nExecuting step {i+1}/{len(steps)}: {step}")
            
            # Simple session check without automatic restart
            if not self.session_manager.check_session():
                message = "Session is not valid. Please restart the app manually."
                print(message)
                results.append({"error": message})
                break
            
            # Execute the current step
            result = self.navigate(step)
            results.append(result)
            
            # Check if the step encountered an error
            if isinstance(result, dict) and "error" in result:
                error_msg = result.get("error", "")
                print(f"Error in step {i+1}: {error_msg}")
                print(f"Stopping multi-step navigation due to error.")
                break
            
            # Wait between steps - use longer wait for transitions that might involve popups
            # or UI that needs time to update/stabilize
            popup_keywords = ["popup", "modal", "overlay", "kaka gir", "ilac gir", "ilaç gir"]
            needs_longer_wait = any(keyword in step.lower() for keyword in popup_keywords)
            
            if i < len(steps) - 1:
                if needs_longer_wait:
                    print(f"Giving extra time for UI to stabilize after popup/overlay interaction...")
                    time.sleep(4)  # Give more time for popup/overlay interactions
                else:
                    time.sleep(2)  # Standard wait between steps
        
        return results
    
    def navigate(self, instruction):
        """
        Navigate in the app based on user instruction
        
        Args:
            instruction: User instruction (e.g., "Click on the login button")
        """
        # Get the current page source with simplified approach
        try:
            # First check if we have a valid session
            if not self.session_manager.check_session():
                return {"error": "Session is not valid. Please restart the app manually."}
            
            page_source = self.session_manager.get_page_source_with_retry()
            if not page_source:
                print("Failed to get page source")
                return {"error": "Failed to get page source"}
        except Exception as e:
            print(f"Error getting page source: {str(e)}")
            return {"error": f"Error getting page source: {str(e)}"}
        
        # Extract available elements for better navigation
        available_elements = extract_available_elements(page_source, 
                                                      platform=self.fetcher.platform if self.fetcher else None)
        
        print(f"Navigating: {instruction}")
        print("\nAvailable interactive elements on screen:")
        print(available_elements)
        
        # Format page source for the LLM
        formatted_source = format_page_source(page_source)
        
        # Get LLM recommendation for navigation
        try:
            response = self.chain.run(
                page_source=formatted_source, 
                user_instruction=instruction,
                available_elements=available_elements
            )
        except Exception as e:
            print(f"Error getting navigation recommendation from LLM: {str(e)}")
            return {"error": f"Failed to get navigation recommendation: {str(e)}"}
        
        try:
            # Parse the JSON response
            action_data = json.loads(response)
            
            # Log what we're going to do
            print(f"Selected element: {action_data.get('identifier', 'Unknown')} ({action_data.get('element_type', 'Unknown')})")
            print(f"Action: {action_data.get('action', 'Unknown')}")
            
            # Execute the recommended action
            action_result = self._execute_action(
                action_data.get("element_type", ""), 
                action_data.get("action", ""), 
                action_data.get("identifier", ""), 
                action_data.get("input_value")
            )
            
            # Merge any error messages from action execution
            if isinstance(action_result, dict) and "error" in action_result:
                action_data["error"] = action_result["error"]
            
            return action_data
        except json.JSONDecodeError:
            error_msg = f"Failed to parse LLM response as JSON: {response}"
            print(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Failed to execute action: {str(e)}"
            print(error_msg)
            return {"error": error_msg}
    
    def _execute_action(self, element_type, action, identifier, input_value=None):
        """Execute the action recommended by the LLM"""
        try:
            # Special handling for scroll_picker action
            if action == "scroll_picker" and input_value and self.picker_handler:
                try:
                    # First, we need to click on the element to make sure the picker is visible
                    element = self.element_finder.find_element(identifier)
                    if element:
                        print(f"Clicking on {identifier} to open the picker")
                        element.click()
                        time.sleep(2)  # Give more time for the picker to appear
                    else:
                        print(f"Warning: Could not find {identifier} element to open picker")
                        # Continue anyway as the picker might already be open
                except Exception as e:
                    print(f"Warning: Error clicking on {identifier}: {str(e)}")
                    # Continue anyway as the picker might already be open
                
                # Check if auto-confirmation is requested
                auto_confirm = "confirm=true" in input_value.lower()
                
                # Remove the confirm=true flag from input_value if present
                clean_input_value = input_value.replace("confirm=true", "").strip()
                
                # Now try to set the value in the picker - with error handling
                try:
                    result = self.picker_handler.handle_scroll_picker(
                        identifier, 
                        clean_input_value,
                        auto_confirm=auto_confirm
                    )
                    
                    if result:
                        if auto_confirm:
                            print("Picker value set and automatically confirmed.")
                        else:
                            print("\n=== PICKER IS WAITING FOR CONFIRMATION ===")
                            print("Picker value set. The picker remains open.")
                            print("Use 'confirm picker' to accept or 'cancel picker' to cancel.")
                            print("=============================================\n")
                        
                        return {"success": True}
                    else:
                        print(f"Failed to set picker value to: {clean_input_value}")
                        return {"error": f"Failed to scroll picker to value: {clean_input_value}"}
                except Exception as e:
                    print(f"Error in scroll picker handling: {str(e)}")
                    return {"error": f"Error in scroll picker: {str(e)}"}
            
            # Special handling for confirm_picker action
            if action == "confirm_picker" and self.picker_handler:
                try:
                    result = self.picker_handler.confirm_picker()
                    if result:
                        return {"success": True}
                    else:
                        return {"error": "Failed to confirm picker selection"}
                except Exception as e:
                    print(f"Error confirming picker: {str(e)}")
                    return {"error": f"Error confirming picker: {str(e)}"}
            
            # Special handling for cancel_picker action
            if action == "cancel_picker" and self.picker_handler:
                try:
                    result = self.picker_handler.cancel_picker()
                    if result:
                        return {"success": True}
                    else:
                        return {"error": "Failed to cancel picker selection"}
                except Exception as e:
                    print(f"Error canceling picker: {str(e)}")
                    return {"error": f"Error canceling picker: {str(e)}"}
            
            # Handle regular click action
            if action == "click":
                try:
                    element = self.element_finder.find_element(identifier)
                    if element:
                        element.click()
                        time.sleep(0.5)  # Short wait for UI to update
                        return {"success": True}
                    else:
                        print(f"Element not found: {identifier}")
                        return {"error": f"Element not found: {identifier}"}
                except Exception as e:
                    print(f"Error clicking element: {str(e)}")
                    return {"error": f"Error clicking element: {str(e)}"}
            
            # Handle input action (typing text)
            if action == "input" and input_value is not None:
                try:
                    element = self.element_finder.find_element(identifier)
                    if element:
                        # Clear existing text (if any) and send new value
                        element.click()  # Focus the element
                        try:
                            element.clear()  # Try to clear existing text
                        except Exception:
                            # Some elements don't support clear
                            pass
                            
                        element.send_keys(input_value)
                        time.sleep(0.5)  # Short wait for UI to update
                        return {"success": True}
                    else:
                        print(f"Input element not found: {identifier}")
                        return {"error": f"Input element not found: {identifier}"}
                except Exception as e:
                    print(f"Error inputting text: {str(e)}")
                    return {"error": f"Error inputting text: {str(e)}"}
            
            # Handle swipe action
            if action == "swipe" and self.fetcher and self.fetcher.driver:
                try:
                    # Get screen dimensions
                    screen_size = self.fetcher.driver.get_window_size()
                    screen_width = screen_size['width']
                    screen_height = screen_size['height']
                    
                    # Determine swipe direction based on identifier
                    direction = identifier.lower()
                    
                    # Start and end coordinates for swipe (relative to screen size)
                    if "up" in direction:
                        # Swipe up (start from bottom-center, end at top-center)
                        start_x = screen_width * 0.5
                        start_y = screen_height * 0.7
                        end_x = screen_width * 0.5
                        end_y = screen_height * 0.3
                    elif "down" in direction:
                        # Swipe down (start from top-center, end at bottom-center)
                        start_x = screen_width * 0.5
                        start_y = screen_height * 0.3
                        end_x = screen_width * 0.5
                        end_y = screen_height * 0.7
                    elif "left" in direction:
                        # Swipe left (start from right-center, end at left-center)
                        start_x = screen_width * 0.8
                        start_y = screen_height * 0.5
                        end_x = screen_width * 0.2
                        end_y = screen_height * 0.5
                    elif "right" in direction:
                        # Swipe right (start from left-center, end at right-center)
                        start_x = screen_width * 0.2
                        start_y = screen_height * 0.5
                        end_x = screen_width * 0.8
                        end_y = screen_height * 0.5
                    else:
                        # Default to swipe up if direction not specified
                        start_x = screen_width * 0.5
                        start_y = screen_height * 0.7
                        end_x = screen_width * 0.5
                        end_y = screen_height * 0.3
                    
                    # Perform swipe
                    self.fetcher.driver.swipe(start_x, start_y, end_x, end_y, 500)  # 500ms swipe duration
                    time.sleep(1)  # Wait for UI to settle after swipe
                    
                    print(f"Performed swipe {direction}")
                    return {"success": True}
                except Exception as e:
                    print(f"Error performing swipe: {str(e)}")
                    return {"error": f"Error performing swipe: {str(e)}"}
            
            # If we get here, the action was not recognized
            return {"error": f"Unsupported action: {action}"}
        
        except Exception as e:
            print(f"Error executing action: {str(e)}")
            return {"error": f"Error executing action: {str(e)}"}
    
    def close(self):
        """Close the app and disconnect from Appium"""
        if self.fetcher:
            self.fetcher.disconnect()
            return True
        return False 