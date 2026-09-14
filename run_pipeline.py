# -*- coding: utf-8 -*-
import subprocess
import sys
import os

def run_script(script_name):
    print(f"\n🚀 Running {script_name}...")
    try:
        # Use sys.executable to ensure we use the same Python interpreter
        result = subprocess.run([sys.executable, script_name], check=True, text=True)
        print(f"✅ {script_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error occurred while running {script_name} (Exit code: {e.returncode})")
        return False

def main():
    print("=========================================================")
    print("🔄 SCM RISK DASHBOARD FULL COMPILATION PIPELINE STARTED")
    print("=========================================================")
    
    # Get directory of current script to run from correct context
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 1. Compile SCM Reports (Market Intelligence Core & History)
    if not run_script("compile_scm_reports.py"):
        sys.exit(1)
        
    # 2. Compile SCM Risk Data (Risk Slices, KPIs, & Sync Backup)
    if not run_script("compile_scm_risk_data.py"):
        sys.exit(1)
        
    print("\n=========================================================")
    print("✨ SCM PIPELINE REBUILD COMPLETE (All Modules Synchronized)")
    print("=========================================================")

if __name__ == "__main__":
    main()
