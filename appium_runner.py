import subprocess, time, os
from appium import webdriver
from selenium.webdriver.common.options import ArgOptions

AAPT_PATH = "C:\\Users\\91908\\AppData\\Local\\Android\\Sdk\\build-tools\\36.1.0\\aapt.exe"

def get_connected_device():
    """Auto-detects any connected device or emulator"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        for line in lines[1:]:
            if "\tdevice" in line:
                device_id = line.split("\t")[0].strip()
                print(f"Device found: {device_id}")
                return device_id
        print("No devices found!")
        return None
    except Exception as e:
        print(f"Detection error: {e}")
    return None

def is_emulator(device_id):
    """Check if device is emulator or real phone"""
    return "emulator" in device_id.lower()

def get_app_info(apk_path):
    """Get package name and launch activity from APK"""
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

def run_tests(apk_path, report_id, screenshots_dir):
    results = []
    driver = None

    try:
        # Step 1: Auto detect device
        device_id = get_connected_device()
        if not device_id:
            results.append({
                "step": "Device Detection",
                "status": "FAILED",
                "detail": "No device or emulator connected!"
            })
            return results

        device_type = "Emulator" if is_emulator(device_id) else "Real Device"
        results.append({
            "step": "Device Detection",
            "status": "PASSED",
            "detail": f"{device_type} found: {device_id}"
        })

        # Step 2: Install APK
        print(f"Installing on {device_type}: {device_id}...")
        install = subprocess.run(
            ["adb", "-s", device_id, "install", "-r", apk_path],
            capture_output=True, text=True
        )
        if "Success" in install.stdout:
            results.append({
                "step": "Install APK",
                "status": "PASSED",
                "detail": f"APK installed on {device_type}"
            })
        else:
            results.append({
                "step": "Install APK",
                "status": "FAILED",
                "detail": install.stderr
            })
            return results

        # Step 3: Get APK info
        package, activity = get_app_info(apk_path)
        if not package or not activity:
            results.append({
                "step": "Read APK Info",
                "status": "FAILED",
                "detail": "Could not read package or activity"
            })
            return results

        results.append({
            "step": "Read APK Info",
            "status": "PASSED",
            "detail": f"Package: {package}"
        })

        # Step 4: Connect Appium
        print(f"Launching {package} on {device_type}...")
        options = ArgOptions()
        options.set_capability("platformName", "Android")
        options.set_capability("appium:automationName", "UiAutomator2")
        options.set_capability("appium:deviceName", device_id)
        options.set_capability("appium:udid", device_id)
        options.set_capability("appium:appPackage", package)
        options.set_capability("appium:appActivity", activity)
        options.set_capability("appium:noReset", True)
        options.set_capability("appium:autoGrantPermissions", True)

        driver = webdriver.Remote(
            command_executor="http://127.0.0.1:4723",
            options=options
        )
        time.sleep(3)

        results.append({
            "step": "App Launch",
            "status": "PASSED",
            "detail": f"App launched on {device_type}: {device_id}"
        })

        # Step 5: Screenshot
        shot_path = f"{screenshots_dir}/launch.png"
        driver.save_screenshot(shot_path)
        results.append({
            "step": "Screenshot",
            "status": "PASSED",
            "detail": "Launch screenshot captured",
            "screenshot": shot_path
        })

        # Step 6: UI Check
        page = driver.page_source
        if page and len(page) > 50:
            results.append({
                "step": "UI Check",
                "status": "PASSED",
                "detail": "App UI loaded successfully"
            })
        else:
            results.append({
                "step": "UI Check",
                "status": "FAILED",
                "detail": "App UI did not load"
            })

        # Step 7: Crash check
        logs = driver.get_log("logcat")
        crashes = [l for l in logs
                   if "FATAL" in str(l) or "ANR" in str(l)]
        if crashes:
            results.append({
                "step": "Crash Check",
                "status": "FAILED",
                "detail": f"{len(crashes)} crash(es) detected!"
            })
        else:
            results.append({
                "step": "Crash Check",
                "status": "PASSED",
                "detail": "No crashes detected"
            })

    except Exception as e:
        results.append({
            "step": "Appium Error",
            "status": "FAILED",
            "detail": str(e)
        })
    finally:
        if driver:
            driver.quit()

    return results
