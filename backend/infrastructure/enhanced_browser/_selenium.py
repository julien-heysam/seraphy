import time
import signal
import threading
import sys
import os
import datetime
import json

from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import traceback
import atexit
import cv2
import numpy as np
import pyautogui

from backend import PROJECT_PATHS
from backend.infrastructure.enhanced_browser.base import EnhancedBrowser


class SeleniumEnhancedBrowser(EnhancedBrowser):
    def __init__(self, chrome_driver_path: str = None):
        # Set up Chrome options
        options = Options()
        options.add_argument("--start-maximized")
        
        # Add user data directory to persist profile data
        user_data_dir = os.path.join(PROJECT_PATHS.RAW_DATA, 'chrome_profile')
        options.add_argument(f'--user-data-dir={user_data_dir}')
        options.add_argument('--profile-directory=Default')
        
        # Additional useful options
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--password-store=basic')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Disable automation info bars
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create the profile directory if it doesn't exist
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)
        
        # Initialize the WebDriver
        self.driver = webdriver.Chrome(options=options)
        
        # Set up cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Vibrant color mapping for different element types with transparent backgrounds
        self.colors = {
            'a': {'color': '#00FFFF', 'bg': 'rgba(0, 255, 255, 0.2)'},      # Bright Cyan
            'button': {'color': '#FF1493', 'bg': 'rgba(255, 20, 147, 0.2)'}, # Deep Pink
            'input': {'color': '#39FF14', 'bg': 'rgba(57, 255, 20, 0.2)'},   # Neon Green
            'select': {'color': '#FF00FF', 'bg': 'rgba(255, 0, 255, 0.2)'},  # Magenta
            'textarea': {'color': '#FF4500', 'bg': 'rgba(255, 69, 0, 0.2)'}, # Neon Orange
            'default': {'color': '#00FF00', 'bg': 'rgba(0, 255, 0, 0.2)'}    # Lime Green
        }
        
        # Screen recording variables
        self.start_time = time.time()
        self.video_output_file = None
        self.recording = False
        self.recorder_thread = None
        self.stop_recording = False
        
        # Action recording variables
        self.action_recording = False
        self.actions = []
        self.action_log_file = None
        
        # Start continuous monitoring
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_page_changes)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        self.output_dir = PROJECT_PATHS.RAW_DATA / 'recordings'
    
    def _signal_handler(self, signum, frame):
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up resources"""
        self._stop_monitor = True
        self.stop_recording = True
        # Save action log before closing
        self._save_action_log()
        if self.recorder_thread and self.recorder_thread.is_alive():
            self.recorder_thread.join(timeout=2)
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
        except:
            pass
    
    def _start_action_recording(self):
        """Start recording user actions"""
        if self.action_recording:
            return
        
        # Reset start time here so that the ts values are relative to the actual start of recording.
        self.start_time = time.time()

        self.action_recording = True
        self.actions = []
        
        # Create timestamp for the log file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory if it doesn't exist
        action_log_dir = os.path.join(self.output_dir, 'action_logs')
        if not os.path.exists(action_log_dir):
            os.makedirs(action_log_dir)
        
        # Set up the log file path
        self.action_log_file = os.path.join(action_log_dir, f'user_actions_{timestamp}.json')
        
        print("Action recording started")
    
    def _record_action(self, action_type, details=None):
        """Record a user action with timestamp"""
        if not self.action_recording:
            return
        
        try:
            # Capture browser state
            page_title = self.driver.title
            page_url = self.driver.current_url
            window_size = self.driver.get_window_size()
            
            # Get current timestamp in multiple formats
            now = datetime.datetime.now()
            iso_timestamp = now.isoformat()
            unix_timestamp = now.timestamp()  # Seconds since epoch as float
            
            # // Get mouse position
            mouse_x, mouse_y = pyautogui.position()
            # breakpoint()
            # Basic action data
            action = {
                'timestamp': iso_timestamp,
                'ts': time.time() - self.start_time,
                'type': action_type,
                'url': page_url,
                'title': page_title,
                'cursor': {
                    'x': mouse_x,
                    'y': mouse_y
                },
                'browserInfo': {
                    'windowWidth': window_size['width'],
                    'windowHeight': window_size['height'],
                    'userAgent': self.driver.execute_script('return navigator.userAgent')
                }
            }
            
            # Add additional details if provided
            if details:
                action.update(details)
            
            # Record action
            self.actions.append(action)
            
            # Save periodically to prevent data loss
            if len(self.actions) % 5 == 0:
                self._save_action_log()
                
            # For debugging purposes, print action type
            print(f"Recorded action: {action_type} at {unix_timestamp}")
        except Exception as e:
            print(f"Error recording action: {str(e)}")
            traceback.print_exc()
    
    def _save_action_log(self):
        """Save recorded actions to a JSON file"""
        if not self.action_recording or not self.actions:
            return
        
        try:
            with open(self.action_log_file, 'w') as f:
                json.dump(self.actions, f, indent=2)
            print(f"Action log saved to: {self.action_log_file}")
        except Exception as e:
            print(f"Error saving action log: {str(e)}")
    
    def _start_recording(self):
        """Start screen recording in a separate thread"""
        if self.recording:
            return
        
        self.recording = True
        self.stop_recording = False
        self.recorder_thread = threading.Thread(target=self._record_screen)
        self.recorder_thread.daemon = True
        self.recorder_thread.start()
        print("Screen recording started")
    
    def _record_screen(self):
        """Record browser window until closed"""
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.join(self.output_dir, 'videos')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Create output file path with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.video_output_file = os.path.join(output_dir, f'browser_session_{timestamp}.mp4')
            
            # Instead of writing frames on the fly, we store them in memory
            frames = []
            record_start = time.time()
            
            # Get initial browser window position and size
            window_rect = self.driver.get_window_rect()
            browser_x = window_rect['x']
            browser_y = window_rect['y']
            browser_width = window_rect['width']
            browser_height = window_rect['height']
            
            # Cursor settings
            cursor_size = 10
            cursor_color = (0, 0, 255)  # Red color for visibility
            cursor_thickness = 2
            
            # Capture frames until stop_recording is set
            # Here we aim for a target of 30 fps if possible.
            target_interval = 1 / 30.0
            while not self.stop_recording:
                frame_start = time.time()
                
                # Update browser window position in each iteration in case it moved/resized
                try:
                    window_rect = self.driver.get_window_rect()
                    browser_x = window_rect['x']
                    browser_y = window_rect['y']
                    browser_width = window_rect['width']
                    browser_height = window_rect['height']
                except:
                    pass
                
                # Get current global mouse position and compute relative position
                mouse_x, mouse_y = pyautogui.position()
                relative_x = mouse_x - browser_x
                relative_y = mouse_y - browser_y
                cursor_in_window = (0 <= relative_x < browser_width and 0 <= relative_y < browser_height)
                
                # Capture screenshot of the browser window
                img = pyautogui.screenshot(region=(browser_x, browser_y, browser_width, browser_height))
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Draw cursor on the frame if it is inside the browser window
                if cursor_in_window:
                    cv2.circle(frame, (relative_x, relative_y), cursor_size, cursor_color, thickness=cursor_thickness)
                    cv2.line(frame, (relative_x - cursor_size, relative_y), (relative_x + cursor_size, relative_y), cursor_color, thickness=cursor_thickness)
                    cv2.line(frame, (relative_x, relative_y - cursor_size), (relative_x, relative_y + cursor_size), cursor_color, thickness=cursor_thickness)
                
                frames.append(frame)
                
                # Sleep to attempt to capture at roughly the target fps
                frame_time = time.time() - frame_start
                sleep_time = max(0, target_interval - frame_time)
                time.sleep(sleep_time)
            
            record_end = time.time()
            duration = record_end - record_start
            if duration <= 0:
                duration = 1  # avoid division by zero
            
            # Compute the effective fps based on recorded duration and frame count.
            effective_fps = len(frames) / duration
            
            # Now write out the video so that playback duration matches the real time.
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.video_output_file, fourcc, effective_fps, (browser_width, browser_height))
            for frame in frames:
                out.write(frame)
            out.release()
            
            print(f"Recording saved to: {self.video_output_file} with duration {duration:.2f} sec and effective fps {effective_fps:.2f}")
            
        except Exception as e:
            print(f"Error during screen recording: {str(e)}")
            traceback.print_exc()
        finally:
            self.recording = False
    
    def _monitor_page_changes(self):
        """Background thread to monitor page changes"""
        last_url = ""
        last_dom_count = 0
        
        while not self._stop_monitor:
            try:
                # Check if URL changed
                current_url = self.driver.current_url
                if current_url != last_url:
                    # Record page navigation action
                    if self.action_recording and last_url:
                        self._record_action('navigation', {
                            'from_url': last_url,
                            'to_url': current_url
                        })
                    
                    time.sleep(1)  # Wait for page to load
                    
                    # Re-inject interaction detection after page change
                    self._inject_interaction_detection()
                    
                    # Re-highlight interactive elements on the new page
                    self.highlight_elements()
                    
                    last_url = current_url
                    last_dom_count = self._get_dom_size()
                    continue
                
                # Check if DOM size changed significantly
                current_dom_count = self._get_dom_size()
                if abs(current_dom_count - last_dom_count) > 5:  # Threshold for DOM changes
                    self.highlight_elements()
                    last_dom_count = current_dom_count
                
                # Check for user interactions like clicks
                interactions = self.driver.execute_script("""
                    const result = {hasInteraction: false, details: null};
                    
                    if (window._lastInteraction && window._lastInteractionDetails) {
                        if (Date.now() - window._lastInteraction < 2000) {
                            result.hasInteraction = true;
                            result.details = window._lastInteractionDetails;
                            // Reset after reading
                            window._lastInteraction = 0;
                            window._lastInteractionDetails = null;
                        }
                    }
                    
                    return result;
                """)
                
                if interactions and interactions.get('hasInteraction') and interactions.get('details'):
                    # Record the detected interaction
                    details = interactions.get('details')
                    details.pop("ts")
                    self._record_action(details.get('type', 'interaction'), details)
                    
                    time.sleep(0.1)  # Wait for any page changes
                    self.highlight_elements()
                
            except Exception as e:
                # Silent exception handling in background thread
                pass
                
            time.sleep(0.5)
    
    def _get_dom_size(self):
        """Get a rough estimate of DOM size to detect changes"""
        try:
            return self.driver.execute_script("return document.getElementsByTagName('*').length")
        except:
            return 0
    
    def _inject_interaction_detection(self):
        """Inject JavaScript to detect user interactions"""
        self.driver.execute_script("""
            if (!window._highlightListenersAdded) {
                window._lastInteraction = 0;
                window._lastInteractionDetails = null;
                
                // Helper Functions for Element Identification
                
                // Get a CSS selector for an element
                function getCssSelector(el) {
                    if (!el) return '';
                    if (el.id) return `#${el.id}`;
                    
                    // Try to build a reasonably unique selector
                    let path = [];
                    let current = el;
                    
                    while (current && current !== document.body && current !== document.documentElement) {
                        // Start with the tag
                        let selector = current.tagName.toLowerCase();
                        
                        // Add id if it has one
                        if (current.id) {
                            selector += `#${current.id}`;
                            path.unshift(selector);
                            break;
                        }
                        
                        // Add classes
                        if (current.classList && current.classList.length) {
                            selector += '.' + Array.from(current.classList).join('.');
                        }
                        
                        // Add position among siblings if needed
                        if (!current.id && !current.classList.length) {
                            let index = 1;
                            let sibling = current.previousElementSibling;
                            
                            while (sibling) {
                                if (sibling.tagName === current.tagName) index++;
                                sibling = sibling.previousElementSibling;
                            }
                            
                            if (index > 1 || !current.previousElementSibling && !current.nextElementSibling) {
                                selector += `:nth-child(${index})`;
                            }
                        }
                        
                        path.unshift(selector);
                        current = current.parentElement;
                        
                        // Limit path length
                        if (path.length >= 5) break;
                    }
                    
                    return path.join(' > ');
                }
                
                // Get an ARIA description for accessibility info
                function getAriaDescription(el) {
                    const ariaAttrs = {};
                    
                    // Common ARIA attributes
                    const ariaAttributes = [
                        'label', 'labelledby', 'describedby', 'hidden', 
                        'expanded', 'haspopup', 'level', 'orientation',
                        'pressed', 'selected', 'checked', 'required', 'invalid'
                    ];
                    
                    ariaAttributes.forEach(attr => {
                        const fullAttr = `aria-${attr}`;
                        if (el.hasAttribute(fullAttr)) {
                            ariaAttrs[fullAttr] = el.getAttribute(fullAttr);
                        }
                    });
                    
                    // Also check role
                    if (el.hasAttribute('role')) {
                        ariaAttrs['role'] = el.getAttribute('role');
                    }
                    
                    return ariaAttrs;
                }
                
                // Get full DOM path
                function getDomPath(el) {
                    const path = [];
                    let current = el;
                    
                    while (current) {
                        let identifier = current.tagName?.toLowerCase();
                        
                        if (current.id) {
                            identifier += `#${current.id}`;
                        } else if (current.className && typeof current.className === 'string') {
                            identifier += `.${current.className.trim().replace(/\\s+/g, '.')}`;
                        }
                        
                        // Add position
                        if (current.parentNode) {
                            const siblings = Array.from(current.parentNode.children || []);
                            const position = siblings.indexOf(current) + 1;
                            if (position > 0) {
                                identifier += `:nth-child(${position})`;
                            }
                        }
                        
                        path.unshift(identifier);
                        current = current.parentNode;
                        
                        if (current === document || current === document.documentElement) {
                            break;
                        }
                    }
                    
                    return path.join(' > ');
                }
                
                // Get better XPath with more attributes
                function getDetailedXPath(element) {
                    // If element has ID, use it for fastest access
                    if (element.id) {
                        return `//*[@id="${element.id}"]`;
                    }
                    
                    // Try to use unique attributes for identification
                    const importantAttrs = ['name', 'class', 'title', 'placeholder', 'data-testid', 'data-test', 'data-cy', 'data-id'];
                    
                    for (const attr of importantAttrs) {
                        if (element.hasAttribute(attr)) {
                            const value = element.getAttribute(attr);
                            // Verify this attribute is somewhat unique
                            const matches = document.querySelectorAll(`[${attr}="${value}"]`);
                            if (matches.length === 1) {
                                return `//*[@${attr}="${value}"]`;
                            }
                        }
                    }
                    
                    // If no unique attribute, build a more precise path
                    const paths = [];
                    let current = element;
                    
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let name = current.nodeName.toLowerCase();
                        
                        // Add attributes to make path more specific
                        let attrs = '';
                        
                        if (current.id) {
                            attrs += `[@id="${current.id}"]`;
                        } else {
                            // Add class if available
                            if (current.className && typeof current.className === 'string' && current.className.trim()) {
                                attrs += `[@class="${current.className.trim()}"]`;
                            }
                            
                            // Add other distinguishing attributes
                            for (const attr of ['name', 'placeholder', 'title']) {
                                if (current.hasAttribute(attr)) {
                                    attrs += `[@${attr}="${current.getAttribute(attr)}"]`;
                                    break; // One is enough
                                }
                            }
                            
                            // If text is short and specific, use it
                            const trimmedText = current.textContent?.trim().substring(0, 20);
                            if (trimmedText && trimmedText.length >= 1 && trimmedText.length <= 20 && !/^\\s*$/.test(trimmedText)) {
                                attrs += `[contains(text(),"${trimmedText.replace(/"/g, '\\"')}")]`;
                            }
                            
                            // Add position if needed
                            if (!attrs) {
                                let position = 1;
                                let sibling = current.previousElementSibling;
                                
                                while (sibling) {
                                    if (sibling.nodeName === current.nodeName) {
                                        position++;
                                    }
                                    sibling = sibling.previousElementSibling;
                                }
                                
                                if (position > 1) {
                                    attrs += `[${position}]`;
                                }
                            }
                        }
                        
                        paths.unshift(name + attrs);
                        current = current.parentNode;
                        
                        // Avoid making paths too long
                        if (paths.length >= 6) {
                            paths.unshift('...');
                            break;
                        }
                    }
                    
                    return '/' + paths.join('/');
                }
                
                // Get computed style summary
                function getStyleSummary(element) {
                    if (!element) return {};
                    
                    const computed = window.getComputedStyle(element);
                    return {
                        display: computed.display,
                        visibility: computed.visibility,
                        position: computed.position,
                        width: computed.width,
                        height: computed.height,
                        color: computed.color,
                        backgroundColor: computed.backgroundColor,
                        fontSize: computed.fontSize,
                        zIndex: computed.zIndex
                    };
                }
                
                // Get element bounding rectangle
                function getBoundingInfo(element) {
                    const rect = element.getBoundingClientRect();
                    return {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        right: rect.right,
                        bottom: rect.bottom,
                        left: rect.left,
                        inViewport: (
                            rect.top >= 0 &&
                            rect.left >= 0 &&
                            rect.bottom <= window.innerHeight &&
                            rect.right <= window.innerWidth
                        )
                    };
                }
                
                // Get surrounding context
                function getSurroundingContext(element) {
                    // Get parent info
                    let parent = element.parentElement;
                    let parentInfo = parent ? {
                        tagName: parent.tagName?.toLowerCase(),
                        id: parent.id || '',
                        classes: parent.className || '',
                        text: parent.textContent?.trim().substring(0, 50) || ''
                    } : null;
                    
                    // Get siblings summary
                    let siblings = {
                        count: 0,
                        similarCount: 0,
                        types: []
                    };
                    
                    if (parent) {
                        const allSiblings = Array.from(parent.children);
                        siblings.count = allSiblings.length;
                        
                        // Count similar siblings (same tag)
                        siblings.similarCount = allSiblings.filter(s => 
                            s.tagName === element.tagName
                        ).length;
                        
                        // Get types of siblings
                        siblings.types = Array.from(new Set(
                            allSiblings.map(s => s.tagName?.toLowerCase())
                        )).slice(0, 5); // Limit to 5 types
                    }
                    
                    return {
                        parent: parentInfo,
                        siblings: siblings,
                        isOnlyChild: siblings.count === 1,
                        hasManySimilarSiblings: siblings.similarCount > 3
                    };
                }
                
                // Get element visibility status
                function getVisibilityStatus(element) {
                    if (!element) return { visible: false };
                    
                    const computed = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    
                    return {
                        visible: !(
                            computed.display === 'none' ||
                            computed.visibility === 'hidden' ||
                            computed.opacity === '0' ||
                            rect.width === 0 ||
                            rect.height === 0
                        ),
                        opacity: computed.opacity,
                        inViewport: (
                            rect.top >= 0 &&
                            rect.left >= 0 &&
                            rect.bottom <= window.innerHeight &&
                            rect.right <= window.innerWidth
                        ),
                        onScreen: (
                            rect.right > 0 &&
                            rect.bottom > 0 &&
                            rect.left < window.innerWidth &&
                            rect.top < window.innerHeight
                        )
                    };
                }
                
                // Get element accessibility info
                function getA11yInfo(element) {
                    if (!element) return {};
                    
                    return {
                        ariaAttributes: getAriaDescription(element),
                        tabIndex: element.tabIndex,
                        hasAccessibleName: !!(
                            element.getAttribute('aria-label') ||
                            element.getAttribute('aria-labelledby') ||
                            element.getAttribute('alt') ||
                            element.title ||
                            (element.tagName === 'BUTTON' && element.textContent.trim())
                        ),
                        isFocusable: element.tabIndex >= 0 || 
                                     ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(element.tagName) ||
                                     element.getAttribute('tabindex') !== null
                    };
                }
                
                // Track clicks with enhanced information
                document.addEventListener('click', function(e) {
                    const now = Date.now();
                    window._lastInteraction = now;
                    
                    // Get element details
                    const target = e.target;
                    const tagName = target.tagName.toLowerCase();
                    const id = target.id || '';
                    const classes = Array.from(target.classList).join(' ') || '';
                    const text = target.textContent?.trim().substring(0, 100) || '';
                    
                    // Get attributes relevant for identification
                    const attrs = {};
                    ['name', 'placeholder', 'type', 'value', 'href', 'src', 'role', 'aria-label', 
                     'title', 'alt', 'data-testid', 'data-id', 'for'].forEach(attr => {
                        if (target.hasAttribute(attr)) {
                            attrs[attr] = target.getAttribute(attr);
                        }
                    });
                    
                    // Create enhanced details object
                    window._lastInteractionDetails = {
                        type: 'click',
                        ts: now / 1000, // Convert to seconds to match Python timestamp
                        element: {
                            tagName,
                            id,
                            classes,
                            text,
                            attributes: attrs,
                            xpath: getDetailedXPath(target),
                            cssSelector: getCssSelector(target),
                            domPath: getDomPath(target),
                            boundingRect: getBoundingInfo(target),
                            visibility: getVisibilityStatus(target),
                            a11y: getA11yInfo(target),
                            style: getStyleSummary(target),
                            context: getSurroundingContext(target)
                        },
                        position: {
                            x: e.clientX,
                            y: e.clientY,
                            pageX: e.pageX,
                            pageY: e.pageY,
                            screenX: e.screenX,
                            screenY: e.screenY,
                            scrollPosition: {
                                scrollX: window.scrollX,
                                scrollY: window.scrollY
                            }
                        },
                        pageInfo: {
                            url: window.location.href,
                            title: document.title,
                            timestamp: new Date().toISOString()
                        }
                    };
                }, true);
                
                // Track form interactions with enhanced information
                document.addEventListener('input', function(e) {
                    const now = Date.now();
                    window._lastInteraction = now;
                    
                    const target = e.target;
                    const tagName = target.tagName.toLowerCase();
                    
                    // Don't capture actual input for password fields
                    const isPassword = target.type === 'password';
                    const inputValue = isPassword ? '[REDACTED]' : target.value;
                    
                    // Get current mouse position
                    const mousePos = {
                        x: window._lastMouseX || 0,
                        y: window._lastMouseY || 0
                    };
                    
                    window._lastInteractionDetails = {
                        type: 'input',
                        ts: now / 1000, // Convert to seconds to match Python timestamp
                        cursor: mousePos,
                        element: {
                            tagName,
                            id: target.id || '',
                            name: target.name || '',
                            type: target.type || '',
                            placeholder: target.placeholder || '',
                            xpath: getDetailedXPath(target),
                            cssSelector: getCssSelector(target),
                            domPath: getDomPath(target),
                            a11y: getA11yInfo(target),
                            boundingRect: getBoundingInfo(target),
                            formInfo: target.form ? {
                                formId: target.form.id || '',
                                formAction: target.form.action || '',
                                formMethod: target.form.method || '',
                                formFields: Array.from(target.form.elements).length
                            } : null
                        },
                        value: inputValue,
                        pageInfo: {
                            url: window.location.href,
                            title: document.title,
                            timestamp: new Date().toISOString()
                        }
                    };
                }, true);
                
                // Track selection changes with enhanced information
                document.addEventListener('change', function(e) {
                    const now = Date.now();
                    window._lastInteraction = now;
                    
                    const target = e.target;
                    const tagName = target.tagName.toLowerCase();
                    
                    // Get current mouse position
                    const mousePos = {
                        x: window._lastMouseX || 0,
                        y: window._lastMouseY || 0
                    };
                    
                    if (tagName === 'select') {
                        const selectedOptions = Array.from(target.selectedOptions).map(opt => ({
                            value: opt.value,
                            text: opt.text,
                            index: opt.index
                        }));
                        
                        window._lastInteractionDetails = {
                            type: 'select',
                            ts: now / 1000, // Convert to seconds to match Python timestamp
                            cursor: mousePos,
                            element: {
                                tagName,
                                id: target.id || '',
                                name: target.name || '',
                                xpath: getDetailedXPath(target),
                                cssSelector: getCssSelector(target),
                                domPath: getDomPath(target),
                                a11y: getA11yInfo(target),
                                boundingRect: getBoundingInfo(target)
                            },
                            selectedOptions,
                            isMultiple: target.multiple,
                            totalOptions: target.options.length,
                            pageInfo: {
                                url: window.location.href,
                                title: document.title,
                                timestamp: new Date().toISOString()
                            }
                        };
                    } else if (tagName === 'input' && (target.type === 'checkbox' || target.type === 'radio')) {
                        window._lastInteractionDetails = {
                            type: target.type,
                            ts: now / 1000, // Convert to seconds to match Python timestamp
                            cursor: mousePos,
                            element: {
                                tagName,
                                id: target.id || '',
                                name: target.name || '',
                                xpath: getDetailedXPath(target),
                                cssSelector: getCssSelector(target),
                                domPath: getDomPath(target),
                                a11y: getA11yInfo(target),
                                boundingRect: getBoundingInfo(target)
                            },
                            checked: target.checked,
                            value: target.value,
                            pageInfo: {
                                url: window.location.href,
                                title: document.title,
                                timestamp: new Date().toISOString()
                            }
                        };
                    }
                }, true);
                
                // Track form submissions with enhanced information
                document.addEventListener('submit', function(e) {
                    const now = Date.now();
                    window._lastInteraction = now;
                    
                    const form = e.target;
                    const formData = {};
                    
                    // Get current mouse position
                    const mousePos = {
                        x: window._lastMouseX || 0,
                        y: window._lastMouseY || 0
                    };
                    
                    // Collect non-sensitive form data
                    Array.from(form.elements).forEach(el => {
                        if (!el.name) return;
                        
                        if (el.type === 'password') {
                            formData[el.name] = '[REDACTED]';
                        } else if (el.type === 'checkbox' || el.type === 'radio') {
                            formData[el.name] = el.checked;
                        } else if (el.tagName === 'SELECT') {
                            formData[el.name] = Array.from(el.selectedOptions).map(o => o.value);
                        } else {
                            formData[el.name] = el.value;
                        }
                    });
                    
                    window._lastInteractionDetails = {
                        type: 'form_submit',
                        ts: now / 1000, // Convert to seconds to match Python timestamp
                        cursor: mousePos,
                        element: {
                            id: form.id || '',
                            action: form.action || '',
                            method: form.method || 'get',
                            xpath: getDetailedXPath(form),
                            cssSelector: getCssSelector(form),
                            domPath: getDomPath(form),
                            enctype: form.enctype || ''
                        },
                        formData,
                        formElements: {
                            count: form.elements.length,
                            types: Array.from(new Set(Array.from(form.elements).map(el => el.type || el.tagName.toLowerCase())))
                        },
                        pageInfo: {
                            url: window.location.href,
                            title: document.title,
                            timestamp: new Date().toISOString()
                        }
                    };
                }, true);
                
                // Track scrolling events
                document.addEventListener('scroll', function(e) {
                    // Only record scroll events occasionally to avoid overwhelming logs
                    const now = Date.now();
                    if (!window._lastScrollTime || now - window._lastScrollTime > 1000) {
                        window._lastScrollTime = now;
                        window._lastInteraction = now;
                        
                        const target = e.target === document ? document.scrollingElement : e.target;
                        
                        // Get current mouse position
                        const mousePos = {
                            x: window._lastMouseX || 0,
                            y: window._lastMouseY || 0
                        };
                        
                        window._lastInteractionDetails = {
                            type: 'scroll',
                            ts: now / 1000, // Convert to seconds to match Python timestamp
                            cursor: mousePos,
                            position: {
                                scrollX: window.scrollX,
                                scrollY: window.scrollY,
                                scrollWidth: document.documentElement.scrollWidth,
                                scrollHeight: document.documentElement.scrollHeight,
                                viewportWidth: window.innerWidth,
                                viewportHeight: window.innerHeight
                            },
                            percentage: {
                                horizontalScroll: Math.round((window.scrollX / (document.documentElement.scrollWidth - window.innerWidth)) * 100) || 0,
                                verticalScroll: Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100) || 0
                            },
                            pageInfo: {
                                url: window.location.href,
                                title: document.title,
                                timestamp: new Date().toISOString()
                            }
                        };
                    }
                }, true);
                
                // Track keyboard events
                document.addEventListener('keydown', function(e) {
                    // Don't record actual key values for input fields to protect privacy
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                        return;
                    }
                    
                    // Only record specific keyboard interactions like navigation, not typing
                    const isNavKey = ['Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 
                                      'Enter', 'Escape', 'Home', 'End', 'PageUp', 'PageDown'].includes(e.key);
                    
                    if (isNavKey) {
                        const now = Date.now();
                        window._lastInteraction = now;
                        
                        // Get current mouse position
                        const mousePos = {
                            x: window._lastMouseX || 0,
                            y: window._lastMouseY || 0
                        };
                        
                        window._lastInteractionDetails = {
                            type: 'keyboard',
                            ts: now / 1000, // Convert to seconds to match Python timestamp
                            cursor: mousePos,
                            key: e.key,
                            modifiers: {
                                alt: e.altKey,
                                ctrl: e.ctrlKey,
                                shift: e.shiftKey,
                                meta: e.metaKey
                            },
                            target: {
                                tagName: e.target.tagName.toLowerCase(),
                                id: e.target.id || '',
                                type: e.target.type || '',
                                xpath: getDetailedXPath(e.target)
                            },
                            pageInfo: {
                                url: window.location.href,
                                title: document.title,
                                timestamp: new Date().toISOString()
                            }
                        };
                    }
                }, true);
                
                // Track mouse movements (throttled)
                let lastMouseX = 0;
                let lastMouseY = 0;
                
                document.addEventListener('mousemove', function(e) {
                    // Update the last known mouse position for other events to use
                    window._lastMouseX = e.clientX;
                    window._lastMouseY = e.clientY;
                    
                    // Only record mouse movements if significant change (> 50px) or every 2 seconds
                    const now = Date.now();
                    const dx = e.clientX - lastMouseX;
                    const dy = e.clientY - lastMouseY;
                    const distance = Math.sqrt(dx*dx + dy*dy);
                    
                    if (distance > 50 || !window._lastMouseTime || now - window._lastMouseTime > 2000) {
                        window._lastMouseTime = now;
                        lastMouseX = e.clientX;
                        lastMouseY = e.clientY;
                        window._lastInteraction = now;
                        
                        // Get element under cursor
                        const elementUnderCursor = document.elementFromPoint(e.clientX, e.clientY);
                        
                        if (elementUnderCursor) {
                            window._lastInteractionDetails = {
                                type: 'mousemove',
                                ts: now / 1000, // Convert to seconds to match Python timestamp
                                position: {
                                    x: e.clientX,
                                    y: e.clientY,
                                    pageX: e.pageX,
                                    pageY: e.pageY
                                },
                                elementUnderCursor: {
                                    tagName: elementUnderCursor.tagName.toLowerCase(),
                                    id: elementUnderCursor.id || '',
                                    classes: Array.from(elementUnderCursor.classList).join(' ') || '',
                                    text: elementUnderCursor.textContent?.trim().substring(0, 30) || '',
                                    xpath: getDetailedXPath(elementUnderCursor)
                                },
                                pageInfo: {
                                    url: window.location.href,
                                    title: document.title,
                                    timestamp: new Date().toISOString()
                                }
                            };
                        }
                    }
                }, true);
                
                // Track hovering
                document.addEventListener('mouseenter', function(e) {
                    // Only record hovers on interactive elements
                    if (e.target.tagName === 'A' || 
                        e.target.tagName === 'BUTTON' || 
                        e.target.tagName === 'INPUT' || 
                        e.target.tagName === 'SELECT' || 
                        e.target.getAttribute('role') === 'button' ||
                        e.target.getAttribute('role') === 'link') {
                        
                        const now = Date.now();
                        window._lastInteraction = now;
                        
                        window._lastInteractionDetails = {
                            type: 'hover',
                            ts: now / 1000, // Convert to seconds to match Python timestamp
                            cursor: {
                                x: e.clientX,
                                y: e.clientY
                            },
                            element: {
                                tagName: e.target.tagName.toLowerCase(),
                                id: e.target.id || '',
                                classes: Array.from(e.target.classList).join(' ') || '',
                                text: e.target.textContent?.trim().substring(0, 50) || '',
                                xpath: getDetailedXPath(e.target)
                            },
                            pageInfo: {
                                url: window.location.href,
                                title: document.title,
                                timestamp: new Date().toISOString()
                            }
                        };
                    }
                }, true);
                
                // Track window resize events
                let lastWidth = window.innerWidth;
                let lastHeight = window.innerHeight;
                
                window.addEventListener('resize', function() {
                    // Only record if significant size change
                    const now = Date.now();
                    const widthDiff = Math.abs(window.innerWidth - lastWidth);
                    const heightDiff = Math.abs(window.innerHeight - lastHeight);
                    
                    // Get current mouse position
                    const mousePos = {
                        x: window._lastMouseX || 0,
                        y: window._lastMouseY || 0
                    };
                    
                    if (widthDiff > 20 || heightDiff > 20) {
                        window._lastInteraction = now;
                        
                        window._lastInteractionDetails = {
                            type: 'resize',
                            ts: now / 1000, // Convert to seconds to match Python timestamp
                            cursor: mousePos,
                            from: {
                                width: lastWidth,
                                height: lastHeight
                            },
                            to: {
                                width: window.innerWidth,
                                height: window.innerHeight
                            },
                            pageInfo: {
                                url: window.location.href,
                                title: document.title,
                                timestamp: new Date().toISOString()
                            }
                        };
                        
                        lastWidth = window.innerWidth;
                        lastHeight = window.innerHeight;
                    }
                }, true);
                
                window._highlightListenersAdded = true;
            }
        """)
    
    def navigate_to(self, url: str) -> None:
        """
        Navigate to a URL and setup highlighting
        
        Args:
            url: The URL to navigate to
        """
        try:
            # Record navigation event
            if self.action_recording:
                current_url = ""
                try:
                    current_url = self.driver.current_url
                except:
                    pass
                
                self._record_action('navigation', {
                    'from_url': current_url,
                    'to_url': url,
                    'method': 'direct_navigation'
                })
            
            self.driver.get(url)
            time.sleep(1)  # Wait for page to load
            self._inject_interaction_detection()
            self.highlight_elements()
            
            # Start recording the browser session and user actions
            self._start_recording()
            self._start_action_recording()
            
            print(f"Navigated to {url}")
            print("Highlighting active - interact with the page or navigate to see highlights update")
            print("Screen recording active - will save when browser is closed")
            print("Action recording active - all interactions will be logged")
            print("Close the browser window to exit")
        except Exception as e:
            print(f"Error navigating to {url}: {str(e)}")
            traceback.print_exc()
    
    def highlight_elements(self):
        """Find and highlight all interactive elements on the page"""
        try:
            # First clean up any existing highlights
            self.driver.execute_script("""
                // Remove existing highlights
                document.querySelectorAll('.element-highlight-box').forEach(box => box.remove());
                document.querySelectorAll('*').forEach(el => {
                    el.style.outline = '';
                    el.style.backgroundColor = '';
                });
            """)
            
            # Update the CSS to use fixed positioning
            self.driver.execute_script("""
                if (!document.getElementById('highlight-styles')) {
                    const style = document.createElement('style');
                    style.id = 'highlight-styles';
                    style.textContent = `
                        .element-highlight-box {
                            position: fixed;
                            font-size: 12px;
                            font-weight: bold;
                            padding: 2px 6px;
                            border-radius: 12px;
                            z-index: 10000;
                            color: white;
                            text-align: center;
                            pointer-events: none;
                            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                        }
                    `;
                    document.head.appendChild(style);
                }
            """)
            
            # Get all interactive elements
            selectors = [
                "button", "a", "input", "select", "textarea", 
                "[role='button']", "[role='link']", "[role='checkbox']", 
                "[onclick]", "[tabindex]:not([tabindex='-1'])"
            ]
            
            # Update the JavaScript that positions the labels
            js_highlight = """
                const elements = [];
                %s.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.offsetWidth && el.offsetHeight && 
                            !el.disabled && 
                            getComputedStyle(el).display !== 'none' && 
                            getComputedStyle(el).visibility !== 'hidden') {
                            elements.push(el);
                        }
                    });
                });
                
                const uniqueElements = [...new Set(elements)];
                
                // Function to update label positions
                function updateLabelPositions() {
                    document.querySelectorAll('.element-highlight-box').forEach(label => {
                        const index = label.getAttribute('data-highlight-for');
                        const el = document.querySelector(`[data-highlight-id="${index}"]`);
                        if (el) {
                            const rect = el.getBoundingClientRect();
                            // Only show labels for elements in viewport
                            if (rect.top >= 0 && rect.left >= 0 && 
                                rect.bottom <= window.innerHeight && 
                                rect.right <= window.innerWidth) {
                                label.style.display = 'block';
                                // Position the label at the top-left corner of the element
                                label.style.top = `${rect.top}px`;
                                label.style.left = `${rect.left}px`;
                            } else {
                                label.style.display = 'none';
                            }
                        }
                    });
                }
                
                // Create highlight boxes
                uniqueElements.forEach((el, index) => {
                    const tagName = el.tagName.toLowerCase();
                    
                    let colorScheme;
                    if (%s[tagName]) {
                        colorScheme = %s[tagName];
                    } else {
                        colorScheme = %s['default'];
                    }
                    
                    el.style.outline = `2px solid ${colorScheme.color}`;
                    el.style.backgroundColor = colorScheme.bg;
                    
                    const label = document.createElement('div');
                    label.className = 'element-highlight-box';
                    label.textContent = (index + 1).toString();
                    label.style.backgroundColor = colorScheme.color;
                    
                    label.setAttribute('data-highlight-for', index);
                    el.setAttribute('data-highlight-id', index);
                    
                    document.body.appendChild(label);
                });

                // Initial position update
                updateLabelPositions();

                // Remove any existing scroll handlers
                if (window._scrollHandler) {
                    window.removeEventListener('scroll', window._scrollHandler);
                }
                
                // Add new scroll handler
                window._scrollHandler = () => {
                    requestAnimationFrame(updateLabelPositions);
                };
                
                window.addEventListener('scroll', window._scrollHandler, { passive: true });
                window.addEventListener('resize', window._scrollHandler, { passive: true });
                
                return uniqueElements.length;
            """ % (selectors, self.colors, self.colors, self.colors)
            
            count = self.driver.execute_script(js_highlight)
            return count
            
        except Exception as e:
            print(f"Error highlighting elements: {str(e)}")
            traceback.print_exc()
            return 0
    
    def run(self) -> None:
        """Main loop - wait until browser is closed"""
        try:
            # Keep running until browser is closed
            while True:
                try:
                    # Check if browser is still open
                    _ = self.driver.current_url
                    time.sleep(0.5)
                except:
                    break
        finally:
            self.cleanup()

if __name__ == "__main__":
    agent = SeleniumEnhancedBrowser()
    agent.navigate_to("https://heysam.ai")
    agent.run()
