from flask import Flask, request, jsonify
import os, uuid, json, threading
from datetime import datetime

app = Flask(__name__)
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

@app.route("/upload-apk", methods=["POST"])
def upload_apk():
    if "apk" not in request.files:
        return jsonify({"status": "error", "report": "No file"})

    apk = request.files["apk"]
    report_id = str(uuid.uuid4())[:8]
    apk_path = os.path.join("uploads", f"{report_id}.apk")
    apk.save(apk_path)

    # ✅ Save basic report IMMEDIATELY so phone gets success
    save_basic_report(report_id, apk.filename)

    # ✅ Run Appium in background AFTER responding
    thread = threading.Thread(
        target=run_appium_background,
        args=(apk_path, report_id)
    )
    thread.daemon = True
    thread.start()

    # ✅ Return immediately — no waiting for Appium!
    return jsonify({
        "status": "success",
        "report": "APK uploaded! Testing started in background.",
        "report_id": report_id
    })

def save_basic_report(report_id, filename):
    """Save instant report so phone gets response fast"""
    report = {
        "id": report_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "RUNNING",
        "filename": filename,
        "summary": {"total": 0, "passed": 0, "failed": 0},
        "steps": [
            {"step": "APK Upload", "status": "PASSED",
             "detail": "File received. Appium testing in progress..."}
        ]
    }
    with open(f"reports/{report_id}.json", "w") as f:
        json.dump(report, f, indent=2)

def run_appium_background(apk_path, report_id):
    """Runs Appium tests after response sent to phone"""
    try:
        from appium_runner import run_tests
        screenshots_dir = f"reports/{report_id}/screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)

        steps = run_tests(apk_path, report_id, screenshots_dir)

        passed = sum(1 for s in steps if s["status"] == "PASSED")
        failed = sum(1 for s in steps if s["status"] == "FAILED")

        # Update report with real Appium results
        report = {
            "id": report_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "PASSED" if failed == 0 else "FAILED",
            "summary": {
                "total": len(steps),
                "passed": passed,
                "failed": failed
            },
            "steps": steps
        }
        with open(f"reports/{report_id}.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"Appium done! Report saved: {report_id}")

    except Exception as e:
        print(f"Appium background error: {e}")

@app.route("/reports", methods=["GET"])
def list_reports():
    reports = []
    for file in os.listdir("reports"):
        if file.endswith(".json"):
            with open(os.path.join("reports", file)) as f:
                data = json.load(f)
                reports.append({
                    "id": data["id"],
                    "status": data["status"],
                    "timestamp": data["timestamp"]
                })
    return jsonify(reports)

@app.route("/reports/<report_id>", methods=["GET"])
def get_report(report_id):
    path = f"reports/{report_id}.json"
    if os.path.exists(path):
        with open(path) as f:
            return jsonify(json.load(f))
    return jsonify({"status": "error"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)