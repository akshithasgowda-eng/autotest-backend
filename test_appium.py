import subprocess
import time
from appium import webdriver
from selenium.webdriver.common.options import ArgOptions

DEVICE_ID = "RZ8T41HQT2T"
APK_PATH = "uploads/f5e296f4.apk"
AAPT_PATH = "C:\\Users\\91908\\AppData\\Local\\Android\\Sdk\\build-tools\\36.1.0\\aapt.exe"

def get_app_info(apk_path):
    try:
        result = subprocess.run(
            [AAPT_PATH, "dump", "badging", apk_path],
            capture_output=True, text=True
        )
        package = None
        activity = None
        for line in result.stdout.split("\n"):
            if line.startswith("package:"):
                package = line.split("name='")[1].split("'")[0]
            if "launchable-activity" in line:
                activity = line.split("name='")[1].split("'")[0]
        return package, activity
    except Exception as e:
        print(f"aapt error: {e}")
    return None, None

print("=== Step 1: Checking device ===")
result = subprocess.run(["adb", "devices"],
                        capture_output=True, text=True)
print(result.stdout)

print("=== Step 2: Getting app info ===")
package, activity = get_app_info(APK_PATH)
print(f"Package:  {package}")
print(f"Activity: {activity}")

if not package or not activity:
    print("ERROR: Could not read APK info!")
    exit()

print("=== Step 3: Connecting to Appium ===")
try:
    options = ArgOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("appium:automationName", "UiAutomator2")
    options.set_capability("appium:deviceName", DEVICE_ID)
    options.set_capability("appium:udid", DEVICE_ID)
    options.set_capability("appium:appPackage", package)
    options.set_capability("appium:appActivity", activity)
    options.set_capability("appium:noReset", True)
    options.set_capability("appium:autoGrantPermissions", True)

    print(f"Launching {package} on phone...")
    driver = webdriver.Remote(
        command_executor="http://127.0.0.1:4723",
        options=options
    )

    print("=== Step 4: App launched! Taking screenshot ===")
    time.sleep(3)
    driver.save_screenshot("test_screenshot.png")
    print("Screenshot saved!")

    print("=== Step 5: Checking for crashes ===")
    logs = driver.get_log("logcat")
    crashes = [l for l in logs if "FATAL" in str(l) or "ANR" in str(l)]
    if crashes:
        print(f"CRASHES FOUND: {len(crashes)}")
    else:
        print("No crashes detected!")

    driver.quit()
    print(f"SUCCESS! {package} fully tested!")

except Exception as e:
    print(f"FAILED: {e}")
