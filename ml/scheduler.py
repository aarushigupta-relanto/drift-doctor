import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import json
import requests
import pandas as pd
from typing import Dict, Any

from ml.drift_detector import run_drift_check

def run_scheduled_check(data_path: str, interval_seconds: int = 60) -> None:
    print(f"[Scheduler] Starting drift check scheduler. Interval: {interval_seconds}s")
    
    try:
        df = pd.read_csv(data_path)
        prod_data = df[df["drift_tag"] == "clean_web"]
    except FileNotFoundError:
        print(f"[Scheduler] Error: Data file not found at {data_path}")
        return
        
    if prod_data.empty:
        print("[Scheduler] Error: No 'clean_web' data available for sampling.")
        return

    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    log_path = os.path.join(reports_dir, "drift_log.jsonl")

    while True:
        try:
            print("[Scheduler] Running scheduled drift check...")
            
            # Sample 200 random rows from production data
            sample_size = min(200, len(prod_data))
            sample_df = prod_data.sample(n=sample_size)
            
            result = run_drift_check(sample_df)
            
            if result.get("drift_detected", False):
                severity = result.get("severity", "UNKNOWN")
                psi = result.get("psi_score", 0.0)
                print(f"[Scheduler] ALERT: Drift detected! Severity: {severity}, PSI: {psi}")
                
                # Write to JSONL
                with open(log_path, "a") as f:
                    f.write(json.dumps(result) + "\n")
                
                # POST to backend
                try:
                    res = requests.post("http://localhost:8000/api/drift", json=result, timeout=5)
                    if res.status_code == 200:
                        print("[Scheduler] Successfully posted drift report to backend.")
                    else:
                        print(f"[Scheduler] Warning: Backend returned status code {res.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"[Scheduler] Warning: Failed to POST to backend. {e}")
            else:
                print("[Scheduler] Check complete. No drift detected.")
                
            time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            print("\n[Scheduler] Stopping scheduler loop.")
            break
        except Exception as e:
            print(f"[Scheduler] Error during check cycle: {e}")
            time.sleep(interval_seconds)

def get_latest_drift_report() -> Dict[str, Any]:
    log_path = os.path.join(os.path.dirname(__file__), "reports", "drift_log.jsonl")
    
    if not os.path.exists(log_path):
        return {"drift_detected": False, "message": "No reports yet"}
        
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            if not lines:
                return {"drift_detected": False, "message": "No reports yet"}
            # Return the last line parsed as JSON
            return json.loads(lines[-1].strip())
    except Exception as e:
        print(f"[Scheduler] Error reading drift log: {e}")
        return {"drift_detected": False, "error": str(e)}

if __name__ == "__main__":
    # Test script execution: run once and exit instead of infinite loop for testing purposes
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(os.path.dirname(base_dir), "final_dataset.csv")
    
    # Run once manually by overriding the sleep or just executing the logic once
    print("[Scheduler] Testing a single iteration of run_scheduled_check...")
    
    try:
        df = pd.read_csv(data_path)
        prod_data = df[df["drift_tag"] == "clean_web"]
        if not prod_data.empty:
            sample_df = prod_data.sample(n=min(200, len(prod_data)))
            res = run_drift_check(sample_df)
            print(f"[Scheduler] Single check result: Drift Detected = {res.get('drift_detected')}")
            # FIX: Write to log so get_latest_drift_report() can be verified
            reports_dir = os.path.join(base_dir, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            log_path = os.path.join(reports_dir, "drift_log.jsonl")
            with open(log_path, "a") as f:
                f.write(json.dumps(res) + "\n")
            print(f"[Scheduler] Written to drift_log.jsonl")

            # Verify read-back
            latest = get_latest_drift_report()
            print(f"[Scheduler] Latest report read back: Drift Detected = {latest.get('drift_detected')}, Severity = {latest.get('severity', 'N/A')}")
        else:
            print("[Scheduler] No prod data found.")
    except Exception as e:
        print(f"[Scheduler] Test failed: {e}")
