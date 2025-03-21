import os
import json
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import MoveTargetOutOfBoundsException

from backend import PROJECT_PATHS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cursor_replay.log')
    ]
)
logger = logging.getLogger('cursor_replay')

def load_action_log(file_path):
    """Load and parse the action log JSON file."""
    try:
        logger.info(f"Loading action log from: {file_path}")
        with open(file_path, 'r') as file:
            actions = json.load(file)
        logger.info(f"Successfully loaded {len(actions)} actions")
        return actions
    except Exception as e:
        logger.error(f"Failed to load action log: {e}", exc_info=True)
        return []

def simulate_cursor_movement(driver, actions, delay=5):
    """
    Simulate cursor movement based on action log data with smooth transitions.
    
    Parameters:
    - driver: Selenium WebDriver instance
    - actions: List of action log entries
    - delay: Delay in seconds between actions (default: 5)
    """
    current_url = None
    
    logger.info(f"Starting cursor movement simulation with {len(actions)} actions")
    
    for i, action in enumerate(actions):
        logger.info(f"Processing action {i+1}/{len(actions)}: {action.get('type', 'unknown')}")
        
        # Handle navigation events
        if action.get('type') == 'navigation':
            target_url = action.get('to_url')
            if target_url and target_url != current_url:
                logger.info(f"Navigating to: {target_url}")
                driver.get(target_url)
                current_url = target_url
                # Wait for page to load
                time.sleep(3)
                
                # Inject CSS to show cursor
                inject_cursor_css(driver)
        
        # Get cursor position
        if 'position' in action:
            target_x = action['position'].get('pageX', 0)
            target_y = action['position'].get('pageY', 0)
            
            logger.info(f"Moving cursor to position: ({target_x}, {target_y})")
            
            try:
                # Get window size to check boundaries
                window_size = driver.get_window_size()
                window_width = window_size['width']
                window_height = window_size['height']
                
                logger.info(f"Current window size: {window_width}x{window_height}")
                
                # Ensure coordinates are within window bounds
                target_x = min(max(0, target_x), window_width - 1)
                target_y = min(max(0, target_y), window_height - 1)
                
                logger.info(f"Adjusted position to: ({target_x}, {target_y})")
                
                # Get current position
                current_position = driver.execute_script("""
                    return {x: window.mouseX || 0, y: window.mouseY || 0};
                """)
                
                current_x = current_position.get('x', 0)
                current_y = current_position.get('y', 0)
                
                # Calculate distance
                distance_x = target_x - current_x
                distance_y = target_y - current_y
                
                # Number of steps for smoother movement
                steps = 15
                
                # Move in smaller increments
                logger.info(f"Moving cursor smoothly from ({current_x}, {current_y}) to ({target_x}, {target_y}) in {steps} steps")
                for j in range(steps):
                    step_x = current_x + (distance_x * (j + 1) / steps)
                    step_y = current_y + (distance_y * (j + 1) / steps)
                    
                    # Update cursor position
                    update_cursor_position(driver, step_x, step_y)
                    
                    # Small delay between steps for visual effect
                    time.sleep(0.05)
                
                # If it's a click, perform the click via JavaScript
                if action.get('type') == 'click':
                    logger.info(f"Clicking at position: ({target_x}, {target_y})")
                    driver.execute_script("""
                        var element = document.elementFromPoint(arguments[0], arguments[1]);
                        if (element) {
                            element.dispatchEvent(new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true,
                                clientX: arguments[0],
                                clientY: arguments[1]
                            }));
                        }
                    """, target_x, target_y)
                
                # If element needs to be found by xpath (optional for some actions)
                if 'elementUnderCursor' in action and 'xpath' in action['elementUnderCursor']:
                    try:
                        xpath = action['elementUnderCursor']['xpath']
                        logger.info(f"Looking for element with xpath: {xpath}")
                        element = driver.find_element(By.XPATH, xpath)
                        logger.info(f"Found element: {element.tag_name}")
                        
                        # For hover actions, highlight the element
                        if action.get('type') == 'hover':
                            logger.info(f"Hovering over element")
                            driver.execute_script("""
                                arguments[0].style.border = '2px solid red';
                                arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                            """, element)
                    except Exception as e:
                        logger.warning(f"Could not find element by xpath: {e}")
                
            except Exception as e:
                logger.warning(f"Failed to move cursor: {e}")
                logger.info("Trying alternative approach...")
                
                try:
                    # Try to directly update cursor position
                    update_cursor_position(driver, target_x, target_y)
                except Exception as e2:
                    logger.error(f"Alternative approach also failed: {e2}")
            
            # Wait between actions
            logger.info(f"Waiting {delay} seconds before next action")
            time.sleep(delay)
    
    logger.info("Cursor movement simulation completed")
    
    # Clean up trail interval
    driver.execute_script("""
        if (window.trailInterval) {
            clearInterval(window.trailInterval);
        }
    """)

def inject_cursor_css(driver):
    """Inject CSS to show a custom cursor with trailing effect."""
    css = """
    #custom-cursor {
        position: fixed;
        width: 20px;
        height: 20px;
        background: rgba(255, 0, 0, 0.7);
        border: 2px solid red;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 9999;
        transition: left 0.3s ease, top 0.3s ease;
        box-shadow: 0 0 10px 2px rgba(255, 0, 0, 0.5);
        animation: pulse 1s infinite alternate;
    }
    
    .cursor-trail {
        position: fixed;
        width: 8px;
        height: 8px;
        background: rgba(255, 0, 0, 0.3);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 9998;
        transition: opacity 1s ease;
    }
    
    @keyframes pulse {
        0% { transform: translate(-50%, -50%) scale(1); }
        100% { transform: translate(-50%, -50%) scale(1.2); }
    }
    """
    
    js_code = """
    /* Remove any existing cursor */
    var existingCursor = document.getElementById('custom-cursor');
    if (existingCursor) existingCursor.remove();
    
    /* Remove any existing trail elements */
    var existingTrails = document.querySelectorAll('.cursor-trail');
    existingTrails.forEach(trail => trail.remove());
    
    /* Add style */
    var style = document.createElement('style');
    style.id = 'cursor-simulator-style';
    style.textContent = arguments[0];
    document.head.appendChild(style);
    
    /* Create cursor element */
    var cursor = document.createElement('div');
    cursor.id = 'custom-cursor';
    cursor.style.left = '50%';
    cursor.style.top = '50%';
    document.body.appendChild(cursor);
    
    /* Create global variables to track position */
    window.mouseX = window.innerWidth / 2;
    window.mouseY = window.innerHeight / 2;
    
    /* Setup trail effect */
    window.trailPoints = [];
    window.createTrailEffect = function() {
        /* Create a new trail point */
        if (window.trailPoints.length >= 5) {
            /* Remove the oldest trail point */
            var oldTrail = window.trailPoints.shift();
            if (oldTrail && oldTrail.parentNode) {
                oldTrail.remove();
            }
        }
        
        var trail = document.createElement('div');
        trail.className = 'cursor-trail';
        trail.style.left = window.mouseX + 'px';
        trail.style.top = window.mouseY + 'px';
        document.body.appendChild(trail);
        window.trailPoints.push(trail);
        
        /* Fade out the trail point */
        setTimeout(() => {
            trail.style.opacity = '0';
        }, 100);
    };
    
    /* Start trail effect */
    window.trailInterval = setInterval(window.createTrailEffect, 100);
    """
    
    # Execute the JavaScript with the CSS as an argument
    driver.execute_script(js_code, css)

def update_cursor_position(driver, x, y):
    """Update the position of the custom cursor with trailing effect."""
    js_code = """
    window.mouseX = arguments[0];
    window.mouseY = arguments[1];
    
    var cursor = document.getElementById('custom-cursor');
    if (cursor) {
        cursor.style.left = arguments[0] + 'px';
        cursor.style.top = arguments[1] + 'px';
    }
    """
    
    driver.execute_script(js_code, x, y)

def replay_action_log(json_file_path):
    """Main function to replay actions from an action log file."""
    logger.info("Starting action log replay")
    
    # Load actions
    actions = load_action_log(json_file_path)
    if not actions:
        logger.error("No actions to replay. Exiting.")
        return
    
    try:
        # Set up Chrome options
        logger.info("Setting up Chrome options...")
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
        
        # Initialize Chrome driver
        logger.info("Initializing Chrome driver...")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 10)
        
        # Execute the action replay
        logger.info("Starting action replay...")
        simulate_cursor_movement(driver, actions, 1)
        
        logger.info("Action replay completed successfully")
    
    except Exception as e:
        logger.error(f"An error occurred during action replay: {e}", exc_info=True)
    
    finally:
        # Keep the browser open for a few seconds
        logger.info("Waiting before closing browser...")
        time.sleep(100)
        
        try:
            logger.info("Closing browser")
            driver.quit()
        except:
            logger.warning("Browser may have already closed")

if __name__ == "__main__":
    # Path to your action log file
    action_log_path = os.path.join(PROJECT_PATHS.RAW_DATA, 'recordings', 'action_logs', 'fake.json')
    
    # Execute the replay
    replay_action_log(action_log_path)