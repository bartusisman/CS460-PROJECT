import xml.etree.ElementTree as ET

def extract_available_elements(page_source, platform=None):
    """Extract a list of available interactive elements from the page source"""
    try:
        available_elements = []
        root = ET.fromstring(page_source)
        
        # Define interactive element types based on platform
        ios_interactive_types = [
            'XCUIElementTypeButton', 
            'XCUIElementTypeCell', 
            'XCUIElementTypeTextField',
            'XCUIElementTypeSwitch',
            'XCUIElementTypeLink',
            'XCUIElementTypeSearchField',
            'XCUIElementTypeTable',
            'XCUIElementTypeStaticText',
            'XCUIElementTypeOther'
        ]
        
        android_interactive_types = [
            'android.widget.Button',
            'android.widget.ImageButton',
            'android.widget.TextView',
            'android.widget.EditText',
            'android.widget.CheckBox',
            'android.widget.Switch',
            'android.widget.RadioButton',
            'android.widget.Spinner',
            'android.widget.ListView',
            'android.view.View'
        ]
        
        # Determine which platform types to use
        if platform == 'android':
            interactive_types = android_interactive_types
        else:
            interactive_types = ios_interactive_types
        
        # Find all elements of interactive types
        for elem_type in interactive_types:
            # Find all elements of this type
            xpath = f".//*[@type='{elem_type}']" if 'XCUI' in elem_type else f".//{elem_type}"
            elements = root.findall(xpath)
            
            for elem in elements:
                # Get element attributes
                attrs = {
                    'type': elem.get('type', elem.tag),
                    'name': elem.get('name', ''),
                    'label': elem.get('label', ''),
                    'text': elem.get('text', ''),
                    'content-desc': elem.get('content-desc', ''),
                    'resource-id': elem.get('resource-id', ''),
                    'value': elem.get('value', ''),
                    'enabled': elem.get('enabled', 'false'),
                    'visible': elem.get('visible', 'false'),
                    'displayed': elem.get('displayed', 'false')
                }
                
                # Skip disabled or invisible elements
                if not (attrs['enabled'] == 'true' or attrs['visible'] == 'true' or attrs['displayed'] == 'true'):
                    continue
                
                # Get the best identifier (name, label, text, content-desc, or resource-id)
                identifier = (attrs['name'] or attrs['label'] or attrs['text'] or 
                             attrs['content-desc'] or attrs['resource-id'] or attrs['value'])
                
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

def detect_popup_state(page_source):
    """Detect if there's a popup/alert/dialog present on the screen"""
    try:
        root = ET.fromstring(page_source)
        
        # iOS popup/alert detection
        ios_alert_xpath = ".//*[contains(@type, 'Alert')]"
        ios_dialog_xpath = ".//*[contains(@type, 'Dialog')]"
        ios_action_sheet_xpath = ".//*[contains(@type, 'ActionSheet')]"
        
        # Android popup/alert detection  
        android_alert_xpath = ".//android.widget.FrameLayout[@resource-id='android:id/content']/*[contains(@resource-id, 'popup') or contains(@resource-id, 'alert') or contains(@resource-id, 'dialog')]"
        android_dialog_xpath = ".//android.app.Dialog"
        
        # Check for iOS alerts
        ios_alerts = root.findall(ios_alert_xpath)
        ios_dialogs = root.findall(ios_dialog_xpath)
        ios_action_sheets = root.findall(ios_action_sheet_xpath)
        
        # Check for Android alerts
        android_alerts = root.findall(android_alert_xpath)
        android_dialogs = root.findall(android_dialog_xpath)
        
        # Check if any popup types were found
        has_popup = (len(ios_alerts) > 0 or 
                    len(ios_dialogs) > 0 or 
                    len(ios_action_sheets) > 0 or
                    len(android_alerts) > 0 or
                    len(android_dialogs) > 0)
        
        if has_popup:
            # Determine popup type
            popup_type = "alert"  # Default type
            
            if len(ios_action_sheets) > 0:
                popup_type = "action_sheet"
            elif len(ios_dialogs) > 0 or len(android_dialogs) > 0:
                popup_type = "dialog"
            
            # Get bounds for popup to help locate elements within it
            bounds = None
            popup_element = None
            
            # Try to find the popup element to get its bounds
            if len(ios_alerts) > 0:
                popup_element = ios_alerts[0]
            elif len(ios_dialogs) > 0:
                popup_element = ios_dialogs[0]
            elif len(ios_action_sheets) > 0:
                popup_element = ios_action_sheets[0]
            elif len(android_alerts) > 0:
                popup_element = android_alerts[0]
            elif len(android_dialogs) > 0:
                popup_element = android_dialogs[0]
            
            # Extract bounds if popup element was found
            if popup_element is not None:
                bounds_str = popup_element.get('bounds') or popup_element.get('frame')
                if bounds_str:
                    # Parse bounds based on format (differs between iOS and Android)
                    try:
                        if '[' in bounds_str:  # Android format: "[left,top][right,bottom]"
                            parts = bounds_str.replace('[', '').replace(']', '').split(',')
                            if len(parts) >= 4:
                                bounds = {
                                    'x': int(parts[0]),
                                    'y': int(parts[1]),
                                    'width': int(parts[2]) - int(parts[0]),
                                    'height': int(parts[3]) - int(parts[1])
                                }
                        elif '{' in bounds_str:  # iOS format: "{{x, y}, {width, height}}"
                            parts = bounds_str.replace('{', '').replace('}', '').replace(' ', '').split(',')
                            if len(parts) >= 4:
                                bounds = {
                                    'x': int(parts[0]),
                                    'y': int(parts[1]),
                                    'width': int(parts[2]),
                                    'height': int(parts[3])
                                }
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing bounds: {e}")
            
            return {
                'has_popup': True,
                'popup_type': popup_type,
                'bounds': bounds
            }
        
        return {'has_popup': False}
    
    except Exception as e:
        print(f"Error detecting popup state: {e}")
        return {'has_popup': False, 'error': str(e)} 