import os
import re
import sys
import time
import io
import csv
import html
import subprocess
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file, Response
from werkzeug.utils import secure_filename
import pdf_generator

# Initialize Flask app
BASE_DIR = Path(__file__).resolve().parent
SUBMISSIONS_DIR = BASE_DIR / "submissions"
REPORTS_DIR = BASE_DIR / "reports"
FINAL_REPORT_PATH = REPORTS_DIR / "final_report.txt"
COMPILE_ERROR_PATH = BASE_DIR / "compile_error.txt"
MAIN_CPP = BASE_DIR / "main.cpp"
TESTCASES_FILE = BASE_DIR / "testcases.txt"

# Cross-platform execution binary name (.exe on Windows, extensionless ELF on Linux)
IS_WINDOWS = sys.platform == "win32"
CHECKER_EXE_NAME = "checker.exe" if IS_WINDOWS else "checker"
CHECKER_EXE = BASE_DIR / CHECKER_EXE_NAME

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload limit

# Enable CORS for decoupled frontend deployment (e.g. Vercel dashboard accessing Render API)
try:
    from flask_cors import CORS
    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    if cors_origins != "*":
        cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)
except ImportError:
    pass


@app.after_request
def add_cors_headers(response):
    """Ensure CORS headers are attached on all /api/ responses for cross-origin frontend support."""
    if request.path.startswith("/api/"):
        origin = request.headers.get("Origin")
        allowed_origins = os.environ.get("CORS_ORIGINS", "*")
        if allowed_origins == "*":
            response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
        elif origin:
            allowed_list = [o.strip() for o in allowed_origins.split(",") if o.strip()]
            if origin in allowed_list:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return response


@app.route("/api/<path:path>", methods=["OPTIONS"])
def api_options_handler(path):
    """Handle pre-flight CORS requests from cross-origin frontends."""
    return "", 204


# Ensure directories exist
SUBMISSIONS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)



DEFAULT_TESTS = [
    {"id": 1, "input": "3 5", "expected": "5"},
    {"id": 2, "input": "9 2", "expected": "9"},
    {"id": 3, "input": "-4 7", "expected": "7"},
]


def load_test_cases_from_file():
    """Reads test cases from testcases.txt or returns default test cases."""
    if not TESTCASES_FILE.exists():
        return list(DEFAULT_TESTS)

    tests = []
    try:
        with open(TESTCASES_FILE, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, 1):
                clean = line.strip()
                if not clean or clean.startswith("#"):
                    continue
                if "|||" in clean:
                    parts = clean.split("|||", 1)
                    tests.append({
                        "id": idx,
                        "input": parts[0].strip(),
                        "expected": parts[1].strip()
                    })
    except Exception as e:
        print(f"Error reading testcases.txt: {e}")
        return list(DEFAULT_TESTS)

    return tests if tests else list(DEFAULT_TESTS)


def save_test_cases_to_file(tests):
    """Saves test cases to testcases.txt in format: <input>|||<expected>."""
    try:
        with open(TESTCASES_FILE, "w", encoding="utf-8") as f:
            for t in tests:
                inp = str(t.get("input", "")).strip()
                exp = str(t.get("expected", "")).strip()
                if inp and exp:
                    f.write(f"{inp}|||{exp}\n")
        return True
    except Exception as e:
        print(f"Error saving testcases.txt: {e}")
        return False


def parse_final_report():
    """Parses reports/final_report.txt into structured submission, test details, and similarity data."""
    if not FINAL_REPORT_PATH.exists():
        return {
            "exists": False,
            "raw_text": "",
            "submissions": [],
            "similarities": [],
            "summary": {
                "total_submissions": 0,
                "successful_compilations": 0,
                "failed_compilations": 0,
                "average_correctness": 0.0,
                "similarity_alerts": 0,
                "max_similarity": 0.0,
            },
            "last_modified": None,
        }

    try:
        with open(FINAL_REPORT_PATH, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()
    except Exception as e:
        return {
            "exists": True,
            "error": f"Failed to read report: {str(e)}",
            "raw_text": "",
            "submissions": [],
            "similarities": [],
            "summary": {},
        }

    # Normalize line endings
    normalized = raw_text.replace("\r\n", "\n")

    # Split report into SUBMISSION RESULTS and PAIRWISE SIMILARITY
    sub_section = ""
    sim_section = ""

    if "SUBMISSION RESULTS" in normalized:
        parts = normalized.split("SUBMISSION RESULTS", 1)[1]
        if "PAIRWISE SIMILARITY" in parts:
            sub_section, sim_section = parts.split("PAIRWISE SIMILARITY", 1)
        else:
            sub_section = parts

    submissions = []
    # Split submission section into individual file blocks
    file_chunks = re.split(r"\n(?=File:\s*)", sub_section.strip())

    for chunk in file_chunks:
        if not chunk.strip().startswith("File:"):
            continue

        file_match = re.search(r"File:\s*([^\n]+)", chunk)
        comp_match = re.search(r"Compilation:\s*([^\n]+)", chunk)
        bracket_match = re.search(r"Bracket Check:\s*([^\n]+)", chunk)
        tests_match = re.search(r"Tests Passed:\s*(\d+)/(\d+)", chunk)
        corr_match = re.search(r"Correctness:\s*([0-9.]+)%?", chunk)

        if not (file_match and comp_match and bracket_match and tests_match and corr_match):
            continue

        filename = file_match.group(1).strip()
        comp = comp_match.group(1).strip()
        bracket = bracket_match.group(1).strip()
        passed_int = int(tests_match.group(1))
        total_int = int(tests_match.group(2))
        corr_float = float(corr_match.group(1))
        compiled_bool = comp.lower() == "successful"
        balanced_bool = bracket.lower() == "balanced"

        # Parse individual test details if present
        test_details = []
        td_matches = re.findall(
            r"Test\s+(\d+):\s+(PASS|FAIL)\s*\|\s*Input:\s*\[(.*?)\]\s*\|\s*Expected:\s*\[(.*?)\]\s*\|\s*Actual:\s*\[(.*?)\]",
            chunk
        )
        for t_idx, status, t_in, t_exp, t_act in td_matches:
            test_details.append({
                "test_num": int(t_idx),
                "passed": status.strip() == "PASS",
                "input": t_in,
                "expected": t_exp,
                "actual": t_act
            })

        # Parse compile error if present
        compile_err = ""
        if "Compile Error:" in chunk:
            err_part = chunk.split("Compile Error:", 1)[1]
            if "Test Details:" in err_part:
                err_part = err_part.split("Test Details:", 1)[0]
            compile_err = err_part.strip()
        elif not compiled_bool:
            compile_err = get_compile_error_log(filename)

        # File stats
        file_path = SUBMISSIONS_DIR / filename
        file_size = file_path.stat().st_size if file_path.exists() else 0

        submissions.append({
            "filename": filename,
            "compilation": comp,
            "compiled": compiled_bool,
            "bracket_check": bracket,
            "balanced": balanced_bool,
            "tests_passed": passed_int,
            "total_tests": total_int,
            "correctness": corr_float,
            "file_size": file_size,
            "test_details": test_details,
            "compile_error": compile_err
        })

    # Parse Pairwise Similarity
    similarities = []
    sim_blocks = re.findall(
        r"([^\n]+?\.cpp)\s+vs\s+([^\n]+?\.cpp)\s*\nToken Similarity:\s*([0-9.]+)%?\s*\nTree Similarity:\s*([0-9.]+)%?\s*\nGraph Similarity:\s*([0-9.]+)%?\s*\nOverall Similarity:\s*([0-9.]+)%?\s*\nStatus:\s*([^\n]+)",
        sim_section,
    )

    similarity_alerts = 0
    max_sim = 0.0

    for item in sim_blocks:
        file1, file2, tok, tree, graph, overall, status = item
        tok_f = float(tok)
        tree_f = float(tree)
        graph_f = float(graph)
        overall_f = float(overall)
        status_clean = status.strip()
        is_alert = overall_f >= 70.0 or "potentially similar" in status_clean.lower()
        if is_alert:
            similarity_alerts += 1
        if overall_f > max_sim:
            max_sim = overall_f

        similarities.append(
            {
                "file1": file1.strip(),
                "file2": file2.strip(),
                "pair_name": f"{file1.strip()} vs {file2.strip()}",
                "token_similarity": tok_f,
                "tree_similarity": tree_f,
                "graph_similarity": graph_f,
                "overall_similarity": overall_f,
                "status": status_clean,
                "is_alert": is_alert,
            }
        )

    # Compute Summary
    total_subs = len(submissions)
    successful_comps = sum(1 for s in submissions if s["compiled"])
    failed_comps = total_subs - successful_comps
    avg_correctness = (
        round(sum(s["correctness"] for s in submissions) / total_subs, 2)
        if total_subs > 0
        else 0.0
    )

    last_modified = None
    if FINAL_REPORT_PATH.exists():
        mtime = FINAL_REPORT_PATH.stat().st_mtime
        last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))

    return {
        "exists": True,
        "raw_text": raw_text,
        "submissions": submissions,
        "similarities": similarities,
        "summary": {
            "total_submissions": total_subs,
            "successful_compilations": successful_comps,
            "failed_compilations": failed_comps,
            "average_correctness": avg_correctness,
            "similarity_alerts": similarity_alerts,
            "max_similarity": round(max_sim, 2),
        },
        "last_modified": last_modified,
    }


def get_compile_error_log(filename=None):
    """Retrieves compilation error from compile_error.txt or tests compiling the file specifically."""
    err_text = ""
    if COMPILE_ERROR_PATH.exists():
        try:
            with open(COMPILE_ERROR_PATH, "r", encoding="utf-8", errors="replace") as f:
                err_text = f.read().strip()
        except Exception:
            err_text = ""

    # If specific filename requested and compile_error.txt doesn't match or is empty, run g++ syntax check
    if filename:
        file_path = SUBMISSIONS_DIR / filename
        if file_path.exists():
            try:
                cmd = ["g++", "-std=c++11", "-fsyntax-only", str(file_path)]
                res = subprocess.run(
                    cmd,
                    cwd=str(BASE_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                )
                if res.returncode != 0 and res.stderr:
                    return res.stderr.strip()
            except Exception as e:
                return f"Error checking syntax: {str(e)}"

    return err_text


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Returns engine readiness, submission count, test cases count, and report status."""
    cpp_files = list(SUBMISSIONS_DIR.glob("*.cpp"))
    checker_ready = CHECKER_EXE.exists()
    report_ready = FINAL_REPORT_PATH.exists()
    test_cases = load_test_cases_from_file()

    last_run = None
    if report_ready:
        mtime = FINAL_REPORT_PATH.stat().st_mtime
        last_run = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))

    return jsonify(
        {
            "status": "ready" if checker_ready else "needs_build",
            "checker_exists": checker_ready,
            "submissions_count": len(cpp_files),
            "test_cases_count": len(test_cases),
            "report_exists": report_ready,
            "last_run": last_run,
            "os": "Windows" if IS_WINDOWS else "Linux",
        }
    )


@app.route("/api/results")
def api_results():
    """Returns parsed results from reports/final_report.txt."""
    data = parse_final_report()
    data["compile_error_log"] = get_compile_error_log()
    return jsonify(data)


@app.route("/api/run-checker", methods=["POST"])
def api_run_checker():
    """Compiles main.cpp if needed and runs checker with latest test cases."""
    start_time = time.time()

    # Always ensure checker is up to date with main.cpp
    needs_compile = not CHECKER_EXE.exists()
    if not needs_compile and MAIN_CPP.exists():
        if MAIN_CPP.stat().st_mtime > CHECKER_EXE.stat().st_mtime:
            needs_compile = True

    if needs_compile:
        try:
            compile_cmd = ["g++", "-std=c++11", "main.cpp", "-o", CHECKER_EXE_NAME]
            build_res = subprocess.run(
                compile_cmd,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            if build_res.returncode != 0:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Failed to compile main.cpp into {CHECKER_EXE_NAME}",
                            "details": build_res.stderr,
                        }
                    ),
                    500,
                )
            if not IS_WINDOWS and CHECKER_EXE.exists():
                try:
                    os.chmod(str(CHECKER_EXE), 0o755)
                except Exception:
                    pass
        except Exception as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Failed to build checker engine: {str(e)}",
                    }
                ),
                500,
            )

    # Check if there are .cpp files in submissions
    cpp_files = sorted([f.name for f in SUBMISSIONS_DIR.glob("*.cpp")])
    if not cpp_files:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "No .cpp files found in submissions directory. Please add student submissions before running the checker.",
                }
            ),
            400,
        )

    # Pre-populate filelist.txt to guarantee consistent file discovery across all OS environments
    try:
        with open(BASE_DIR / "filelist.txt", "w", encoding="utf-8") as fl:
            for fname in cpp_files:
                fl.write(f"{fname}\n")
    except Exception as e:
        print(f"Warning: could not write filelist.txt: {e}")

    # Execute checker binary
    try:
        checker_cmd = [str(CHECKER_EXE)] if IS_WINDOWS else [f"./{CHECKER_EXE_NAME}"]
        run_res = subprocess.run(
            checker_cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        elapsed_sec = round(time.time() - start_time, 2)

        # Parse new results immediately
        results = parse_final_report()
        results["compile_error_log"] = get_compile_error_log()

        return jsonify(
            {
                "success": run_res.returncode == 0,
                "elapsed_seconds": elapsed_sec,
                "stdout": run_res.stdout,
                "stderr": run_res.stderr,
                "results": results,
            }
        )
    except subprocess.TimeoutExpired:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Checker execution timed out (limit: 60s). Check for infinite loops in student code.",
                }
            ),
            500,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Execution error: {str(e)}",
                }
            ),
            500,
        )


@app.route("/api/submissions", methods=["GET"])
def api_list_submissions():
    """Lists all submissions with file size, line counts, and priority queue ordering."""
    if not SUBMISSIONS_DIR.exists():
        return jsonify([])

    items = []
    for f in sorted(SUBMISSIONS_DIR.glob("*.cpp")):
        stat = f.stat()
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as file_content:
                lines = file_content.readlines()
                line_count = len(lines)
        except Exception:
            line_count = 0

        items.append(
            {
                "filename": f.name,
                "size_bytes": stat.st_size,
                "lines": line_count,
                "priority": stat.st_size,  # Priority in Max Heap is based on file size
                "modified": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)
                ),
            }
        )

    # Order items descending by priority (matching Max Heap execution order)
    items.sort(key=lambda x: x["priority"], reverse=True)
    return jsonify(items)


@app.route("/api/submissions/<filename>", methods=["GET"])
def api_get_submission_content(filename):
    """Returns raw source code, compilation error, and individual test results for a submission."""
    safe_name = secure_filename(filename)
    if not safe_name.endswith(".cpp"):
        return jsonify({"error": "Invalid file format. Must be a .cpp file."}), 400

    target = SUBMISSIONS_DIR / safe_name
    if not target.exists():
        return jsonify({"error": f"File '{safe_name}' not found."}), 404

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        compile_err = get_compile_error_log(safe_name)

        # Retrieve test details from latest report if available
        report_data = parse_final_report()
        sub_info = next((s for s in report_data["submissions"] if s["filename"] == safe_name), None)

        return jsonify(
            {
                "filename": safe_name,
                "content": content,
                "compile_error": compile_err,
                "size": target.stat().st_size,
                "test_details": sub_info.get("test_details", []) if sub_info else [],
                "compilation": sub_info.get("compilation", "Unknown") if sub_info else "Unknown",
                "tests_passed": sub_info.get("tests_passed", 0) if sub_info else 0,
                "total_tests": sub_info.get("total_tests", 0) if sub_info else 0,
                "correctness": sub_info.get("correctness", 0.0) if sub_info else 0.0,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/submissions/<filename>", methods=["DELETE"])
@app.route("/api/submissions/<filename>/delete", methods=["POST", "DELETE"])
def api_delete_submission(filename):
    """Deletes a student submission file from submissions/ and cleans up any compiled binary."""
    safe_name = secure_filename(filename)
    if not safe_name.endswith(".cpp"):
        return jsonify({"success": False, "error": "Only .cpp submission files can be deleted."}), 400

    target = SUBMISSIONS_DIR / safe_name
    if not target.is_file():
        return jsonify({"success": False, "error": f"Submission '{safe_name}' not found."}), 404

    try:
        target.unlink()

        # Clean up any generated binary executable if present in submissions or base directory
        stem = target.stem
        for ext in [".exe", ""]:
            sub_exe = SUBMISSIONS_DIR / f"{stem}{ext}"
            if sub_exe.is_file():
                try:
                    sub_exe.unlink()
                except Exception:
                    pass

        for exe in BASE_DIR.glob(f"{stem}*"):
            if exe.is_file() and (exe.suffix == ".exe" or not exe.suffix):
                try:
                    exe.unlink()
                except Exception:
                    pass

        return jsonify({
            "success": True,
            "message": f"Successfully deleted submission '{safe_name}'.",
            "filename": safe_name
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to delete '{safe_name}': {str(e)}"}), 500


@app.route("/api/submissions/upload", methods=["POST"])
def api_upload_submission():
    """Uploads a .cpp file or creates one from code editor text with overwrite safety."""
    # Check if this is a multipart file upload
    if "file" in request.files:
        uploaded_file = request.files["file"]
        if not uploaded_file or uploaded_file.filename == "":
            return jsonify({"success": False, "error": "No file selected."}), 400

        filename = secure_filename(uploaded_file.filename)
        if not filename.endswith(".cpp"):
            return (
                jsonify(
                    {"success": False, "error": "Only .cpp files are permitted."}
                ),
                400,
            )

        allow_overwrite = request.form.get("overwrite", "false").lower() == "true"
        target_path = SUBMISSIONS_DIR / filename

        if target_path.exists() and not allow_overwrite:
            return (
                jsonify(
                    {
                        "success": False,
                        "exists": True,
                        "error": f"File '{filename}' already exists. Enable overwrite to replace it.",
                    }
                ),
                409,
            )

        uploaded_file.save(str(target_path))
        return jsonify(
            {
                "success": True,
                "message": f"Successfully added '{filename}'.",
                "filename": filename,
            }
        )

    # Check if this is raw code text creation
    data = request.get_json(silent=True) or request.form
    code_text = data.get("code")
    filename = data.get("filename")

    if not code_text or not filename:
        return (
            jsonify(
                {"success": False, "error": "Both filename and code are required."}
            ),
            400,
        )

    filename = secure_filename(filename)
    if not filename.endswith(".cpp"):
        filename += ".cpp"

    allow_overwrite = str(data.get("overwrite", "false")).lower() == "true"
    target_path = SUBMISSIONS_DIR / filename

    if target_path.exists() and not allow_overwrite:
        return (
            jsonify(
                {
                    "success": False,
                    "exists": True,
                    "error": f"File '{filename}' already exists. Enable overwrite to replace it.",
                }
            ),
            409,
        )

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code_text)
        return jsonify(
            {
                "success": True,
                "message": f"Successfully created '{filename}'.",
                "filename": filename,
            }
        )
    except Exception as e:
        return (
            jsonify(
                {"success": False, "error": f"Failed to save file: {str(e)}"}
            ),
            500,
        )


@app.route("/api/compile-error/<filename>")
def api_compile_error(filename):
    """Returns specific compilation error for a submission file."""
    safe_name = secure_filename(filename)
    err = get_compile_error_log(safe_name)
    return jsonify({"filename": safe_name, "error": err})


@app.route("/api/similarity/pair")
def api_similarity_pair():
    """Returns source code and exact pairwise similarity scores for two student files."""
    file1 = request.args.get("file1", "")
    file2 = request.args.get("file2", "")

    safe_f1 = secure_filename(file1)
    safe_f2 = secure_filename(file2)

    path1 = SUBMISSIONS_DIR / safe_f1
    path2 = SUBMISSIONS_DIR / safe_f2

    content1 = ""
    content2 = ""

    if path1.exists():
        with open(path1, "r", encoding="utf-8", errors="replace") as f:
            content1 = f.read()

    if path2.exists():
        with open(path2, "r", encoding="utf-8", errors="replace") as f:
            content2 = f.read()

    # Find similarity metrics from report
    report_data = parse_final_report()
    matched_pair = None
    for p in report_data.get("similarities", []):
        if (p["file1"] == safe_f1 and p["file2"] == safe_f2) or (p["file1"] == safe_f2 and p["file2"] == safe_f1):
            matched_pair = p
            break

    if not matched_pair:
        matched_pair = {
            "pair_name": f"{safe_f1} vs {safe_f2}",
            "token_similarity": 0.0,
            "tree_similarity": 0.0,
            "graph_similarity": 0.0,
            "overall_similarity": 0.0,
            "status": "No High Similarity Detected",
            "is_alert": False
        }

    return jsonify({
        "file1": safe_f1,
        "file2": safe_f2,
        "content1": content1,
        "content2": content2,
        "metrics": matched_pair,
        "disclaimer": "NOTE: Structural similarity metrics are indicators of textual and structural resemblance only. High similarity does not prove plagiarism or misconduct."
    })


@app.route("/api/report/raw")
def api_raw_report():
    """Returns raw content of reports/final_report.txt."""
    if not FINAL_REPORT_PATH.exists():
        return jsonify({"error": "Report file does not exist yet."}), 404

    try:
        with open(FINAL_REPORT_PATH, "r", encoding="utf-8", errors="replace") as f:
            return jsonify({"content": f.read()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/report/download")
def api_download_report():
    """Sends final_report.txt as a downloadable text file."""
    if not FINAL_REPORT_PATH.exists():
        return jsonify({"error": "Report file not found. Run the checker first."}), 404

    return send_file(
        str(FINAL_REPORT_PATH),
        mimetype="text/plain",
        as_attachment=True,
        download_name="final_report.txt"
    )


@app.route("/api/report/pdf")
def api_download_report_pdf():
    """Generates and serves a formatted, readable PDF of the final evaluation report."""
    if not FINAL_REPORT_PATH.exists():
        return jsonify({"error": "Report file not found. Run the checker first."}), 404

    try:
        data = parse_final_report()
        pdf_bytes = pdf_generator.build_final_report_pdf(data)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="assigncheck_evaluation_report.pdf"'}
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF report: {str(e)}"}), 500


@app.route("/api/report/export-submissions-csv")
def api_export_submissions_csv():
    """Exports submissions results as a properly escaped downloadable CSV."""
    data = parse_final_report()
    output = io.StringIO()
    # Write UTF-8 BOM for Microsoft Excel compatibility
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "Filename",
        "Compilation_Status",
        "Bracket_Check",
        "Tests_Passed",
        "Total_Tests",
        "Correctness_Percent",
        "File_Size_Bytes",
        "Test_Details",
        "Compile_Error"
    ])

    for sub in data.get("submissions", []):
        test_summary_parts = []
        for td in sub.get("test_details", []):
            st = "PASS" if td.get("passed") else "FAIL"
            test_summary_parts.append(f"T{td.get('test_num')}:{st} [In: {td.get('input')} | Exp: {td.get('expected')} | Act: {td.get('actual')}]")
        test_summary_str = "; ".join(test_summary_parts) if test_summary_parts else "N/A"

        writer.writerow([
            sub.get("filename", ""),
            sub.get("compilation", ""),
            sub.get("bracket_check", ""),
            sub.get("tests_passed", 0),
            sub.get("total_tests", 0),
            sub.get("correctness", 0.0),
            sub.get("file_size", 0),
            test_summary_str,
            sub.get("compile_error", "")
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="assigncheck_submissions.csv"'}
    )


@app.route("/api/report/export-similarity-csv")
def api_export_similarity_csv():
    """Exports pairwise similarity results as a properly escaped downloadable CSV."""
    data = parse_final_report()
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "Submission_1",
        "Submission_2",
        "Token_Similarity_Percent",
        "Tree_Similarity_Percent",
        "Graph_Similarity_Percent",
        "Overall_Similarity_Percent",
        "Status",
        "Alert_Flag"
    ])

    for sim in data.get("similarities", []):
        writer.writerow([
            sim.get("file1", ""),
            sim.get("file2", ""),
            sim.get("token_similarity", 0.0),
            sim.get("tree_similarity", 0.0),
            sim.get("graph_similarity", 0.0),
            sim.get("overall_similarity", 0.0),
            sim.get("status", ""),
            "ALERT" if sim.get("is_alert") else "NORMAL"
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="assigncheck_similarity.csv"'}
    )


@app.route("/api/report/export-csv")
@app.route("/api/report/export-results-csv")
def api_export_results_csv():
    """Exports comprehensive evaluation results (submissions + pairwise similarity) as a downloadable CSV."""
    data = parse_final_report()
    summary = data.get("summary", {})
    last_mod = data.get("last_modified") or time.strftime("%Y-%m-%d %H:%M:%S")

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # 1. Summary metadata block
    writer.writerow(["# ASSIGNCHECK EVALUATION RESULTS REPORT"])
    writer.writerow(["# Last Evaluated", last_mod])
    writer.writerow(["# Total Submissions", summary.get("total_submissions", len(data.get("submissions", [])))])
    writer.writerow(["# Successful Compilations", summary.get("successful_compilations", 0)])
    writer.writerow(["# Failed Compilations", summary.get("failed_compilations", 0)])
    writer.writerow(["# Average Correctness (%)", summary.get("average_correctness", 0.0)])
    writer.writerow(["# Similarity Alerts (>=70%)", summary.get("similarity_alerts", 0)])
    writer.writerow(["# Max Similarity (%)", summary.get("max_similarity", 0.0)])
    writer.writerow([])

    # 2. Submissions Section
    writer.writerow(["[SUBMISSION EVALUATION RESULTS]"])
    writer.writerow([
        "Filename",
        "Compilation_Status",
        "Bracket_Check",
        "Tests_Passed",
        "Total_Tests",
        "Correctness_Percent",
        "File_Size_Bytes",
        "Test_Case_Statuses",
        "Compile_Diagnostics"
    ])

    for sub in data.get("submissions", []):
        test_parts = []
        for td in sub.get("test_details", []):
            st = "PASS" if td.get("passed") else "FAIL"
            test_parts.append(f"T{td.get('test_num')}:{st} (Input: [{td.get('input')}], Expected: [{td.get('expected')}], Actual: [{td.get('actual')}])")
        test_summary_str = "; ".join(test_parts) if test_parts else "N/A"

        writer.writerow([
            sub.get("filename", ""),
            sub.get("compilation", ""),
            sub.get("bracket_check", ""),
            sub.get("tests_passed", 0),
            sub.get("total_tests", 0),
            sub.get("correctness", 0.0),
            sub.get("file_size", 0),
            test_summary_str,
            sub.get("compile_error", "")
        ])

    writer.writerow([])

    # 3. Pairwise Similarity Section
    writer.writerow(["[PAIRWISE STRUCTURAL SIMILARITY ANALYSIS]"])
    writer.writerow([
        "Submission_1",
        "Submission_2",
        "Token_Similarity_Percent",
        "Tree_Similarity_Percent",
        "Graph_Similarity_Percent",
        "Overall_Similarity_Percent",
        "Status",
        "Alert_Flag"
    ])

    for sim in data.get("similarities", []):
        writer.writerow([
            sim.get("file1", ""),
            sim.get("file2", ""),
            sim.get("token_similarity", 0.0),
            sim.get("tree_similarity", 0.0),
            sim.get("graph_similarity", 0.0),
            sim.get("overall_similarity", 0.0),
            sim.get("status", ""),
            "ALERT" if sim.get("is_alert") else "NORMAL"
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="assigncheck_evaluation_results.csv"'}
    )


@app.route("/api/similarity/export-comparison")
def api_export_comparison():
    """Downloads side-by-side code comparison as a formatted, readable HTML report or plain text."""
    file1 = request.args.get("file1", "")
    file2 = request.args.get("file2", "")
    fmt = request.args.get("format", "html").lower().strip()

    safe_f1 = secure_filename(file1)
    safe_f2 = secure_filename(file2)

    if not safe_f1 or not safe_f2 or safe_f1 == safe_f2:
        return jsonify({"error": "Please select two distinct submission files to compare."}), 400

    if not safe_f1.endswith(".cpp") or not safe_f2.endswith(".cpp"):
        return jsonify({"error": "Only .cpp submission files can be compared."}), 400

    path1 = SUBMISSIONS_DIR / safe_f1
    path2 = SUBMISSIONS_DIR / safe_f2

    if not path1.is_file() or not path2.is_file():
        return jsonify({"error": "One or both selected submission files do not exist."}), 404

    try:
        with open(path1, "r", encoding="utf-8", errors="replace") as f:
            content1 = f.read()
        with open(path2, "r", encoding="utf-8", errors="replace") as f:
            content2 = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read submission files: {str(e)}"}), 500

    report_data = parse_final_report()
    matched_pair = next(
        (p for p in report_data.get("similarities", [])
         if (p["file1"] == safe_f1 and p["file2"] == safe_f2) or (p["file1"] == safe_f2 and p["file2"] == safe_f1)),
        {
            "token_similarity": 0.0,
            "tree_similarity": 0.0,
            "graph_similarity": 0.0,
            "overall_similarity": 0.0,
            "status": "No High Similarity Detected",
            "is_alert": False
        }
    )

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")

    if fmt == "txt":
        lines1 = content1.splitlines()
        lines2 = content2.splitlines()
        max_lines = max(len(lines1), len(lines2))

        out = [
            "=" * 84,
            "ASSIGNCHECK - PAIRWISE CODE COMPARISON REPORT",
            "=" * 84,
            f"Submission A: {safe_f1}",
            f"Submission B: {safe_f2}",
            f"Generated:    {timestamp_str}",
            "",
            "STRUCTURAL SIMILARITY METRICS:",
            f"- Overall Match:           {matched_pair.get('overall_similarity', 0.0)}%",
            f"- Token Multiset (50%):    {matched_pair.get('token_similarity', 0.0)}%",
            f"- Tree Block Struct (25%): {matched_pair.get('tree_similarity', 0.0)}%",
            f"- Graph Transitions (25%): {matched_pair.get('graph_similarity', 0.0)}%",
            f"- Alert Status:            {matched_pair.get('status', 'Unknown')}",
            "",
            "DISCLAIMER:",
            "Structural similarity metrics indicate textual and structural resemblance only.",
            "High similarity does NOT independently prove plagiarism or academic dishonesty.",
            "-" * 84,
            f"{'Line':<5} | {'Diff':<4} | {safe_f1:<44} | {safe_f2}",
            "-" * 84,
        ]

        set1 = set(l.strip() for l in lines1 if l.strip())
        set2 = set(l.strip() for l in lines2 if l.strip())

        for i in range(max_lines):
            l1 = lines1[i] if i < len(lines1) else ""
            l2 = lines2[i] if i < len(lines2) else ""
            mark = "  "
            if l1.strip() != l2.strip():
                mark = "! "
            out.append(f"{i+1:<5} | {mark:<4} | {l1[:42]:<44} | {l2}")

        out.append("=" * 84)
        return Response(
            "\n".join(out),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="comparison_{safe_f1}_vs_{safe_f2}.txt"'}
        )

    # HTML format
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()
    set2 = set(l.strip() for l in lines2 if l.strip())
    set1 = set(l.strip() for l in lines1 if l.strip())

    rows1_html = "".join([
        f'<div class="row {"del" if l.strip() and l.strip() not in set2 else ""}"><span class="num">{idx+1}</span><span class="sign">{"-" if l.strip() and l.strip() not in set2 else " "}</span><span class="txt">{html.escape(l)}</span></div>'
        for idx, l in enumerate(lines1)
    ])
    rows2_html = "".join([
        f'<div class="row {"add" if l.strip() and l.strip() not in set1 else ""}"><span class="num">{idx+1}</span><span class="sign">{"+" if l.strip() and l.strip() not in set1 else " "}</span><span class="txt">{html.escape(l)}</span></div>'
        for idx, l in enumerate(lines2)
    ])

    alert_class = "alert" if matched_pair.get("is_alert") else ""
    status_str = matched_pair.get("status", "Unknown")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AssignCheck Comparison: {safe_f1} vs {safe_f2}</title>
<style>
:root {{
    --bg-base: #080c14;
    --bg-surface: #0f172a;
    --bg-surface-elevated: #15203b;
    --border-color: rgba(255, 255, 255, 0.08);
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --accent-indigo: #6366f1;
    --status-danger: #ef4444;
    --status-success: #10b981;
}}
body {{
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    background: var(--bg-base);
    color: var(--text-primary);
    margin: 0;
    padding: 24px;
    line-height: 1.5;
}}
.container {{ max-width: 1400px; margin: 0 auto; }}
.header {{
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
}}
.title-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
}}
h1 {{
    font-size: 1.35rem;
    margin: 0;
    font-family: 'JetBrains Mono', Consolas, monospace;
    color: #f8fafc;
}}
.badge {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}}
.badge-danger {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}
.badge-neutral {{ background: rgba(255, 255, 255, 0.08); color: #cbd5e1; }}
.time-tag {{ font-size: 0.8rem; color: #94a3b8; font-family: monospace; }}
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-top: 14px;
}}
.metric-card {{
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 14px;
}}
.metric-label {{ font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
.metric-val {{
    font-size: 1.25rem;
    font-weight: bold;
    font-family: 'JetBrains Mono', Consolas, monospace;
    color: #38bdf8;
    margin-top: 4px;
}}
.metric-val.alert {{ color: #ef4444; }}
.disclaimer {{
    background: rgba(245, 158, 11, 0.08);
    border-left: 4px solid #f59e0b;
    padding: 12px 16px;
    border-radius: 4px;
    font-size: 0.82rem;
    color: #fde68a;
    margin-bottom: 20px;
    line-height: 1.4;
}}
.grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}
.col {{
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    overflow: hidden;
}}
.col-head {{
    background: #1e293b;
    padding: 10px 16px;
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 0.9rem;
    font-weight: bold;
    border-bottom: 1px solid var(--border-color);
    color: #e2e8f0;
    display: flex;
    justify-content: space-between;
}}
.code-area {{
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
    font-size: 0.82rem;
    max-height: 720px;
    overflow-y: auto;
    background: #060911;
}}
.row {{
    display: flex;
    line-height: 1.6;
    border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}}
.num {{
    width: 44px;
    text-align: right;
    padding-right: 10px;
    color: #64748b;
    background: rgba(0, 0, 0, 0.35);
    border-right: 1px solid var(--border-color);
    user-select: none;
    flex-shrink: 0;
}}
.sign {{
    width: 16px;
    text-align: center;
    font-weight: bold;
    user-select: none;
    flex-shrink: 0;
}}
.txt {{
    padding-left: 8px;
    white-space: pre;
    flex: 1;
    overflow-x: visible;
}}
.row.del {{
    background: rgba(239, 68, 68, 0.16);
    color: #fca5a5;
}}
.row.del .sign {{ color: #ef4444; }}
.row.add {{
    background: rgba(16, 185, 129, 0.16);
    color: #6ee7b7;
}}
.row.add .sign {{ color: #10b981; }}
@media (max-width: 900px) {{
    .grid {{ grid-template-columns: 1fr; }}
}}
@media print {{
    body {{ background: #fff; color: #000; padding: 0; }}
    .header, .col {{ border: 1px solid #ccc; background: #fff; color: #000; }}
    .col-head {{ background: #eee; color: #000; }}
    .code-area {{ max-height: none; overflow: visible; background: #fafafa; color: #000; }}
    .row.del {{ background: #ffebee; color: #b71c1c; }}
    .row.add {{ background: #e8f5e9; color: #1b5e20; }}
    .num {{ background: #eee; color: #555; border-right: 1px solid #ccc; }}
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title-row">
      <h1>{safe_f1} vs {safe_f2}</h1>
      <span class="time-tag">Exported: {timestamp_str}</span>
    </div>
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Overall Match</div>
        <div class="metric-val {alert_class}">{matched_pair.get('overall_similarity', 0.0)}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Token Multiset (50%)</div>
        <div class="metric-val">{matched_pair.get('token_similarity', 0.0)}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Tree Block Structure (25%)</div>
        <div class="metric-val">{matched_pair.get('tree_similarity', 0.0)}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Graph Transitions (25%)</div>
        <div class="metric-val">{matched_pair.get('graph_similarity', 0.0)}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Alert Status</div>
        <div class="metric-val" style="font-size: 0.95rem;">
          <span class="badge {'badge-danger' if matched_pair.get('is_alert') else 'badge-neutral'}">{status_str}</span>
        </div>
      </div>
    </div>
  </div>

  <div class="disclaimer">
    <strong>Academic Disclaimer:</strong> Structural similarity metrics are mathematical indicators of token multiset, scope-nesting, and sequential transition likeness. High similarity does NOT independently prove plagiarism or academic dishonesty.
  </div>

  <div class="grid">
    <div class="col">
      <div class="col-head"><span>{safe_f1}</span><span style="font-size: 0.8rem; font-weight: normal; color: #94a3b8;">{len(lines1)} lines</span></div>
      <div class="code-area">{rows1_html}</div>
    </div>
    <div class="col">
      <div class="col-head"><span>{safe_f2}</span><span style="font-size: 0.8rem; font-weight: normal; color: #94a3b8;">{len(lines2)} lines</span></div>
      <div class="code-area">{rows2_html}</div>
    </div>
  </div>
</div>
</body>
</html>"""

    return Response(
        html_content,
        mimetype="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="comparison_{safe_f1}_vs_{safe_f2}.html"'}
    )


@app.route("/api/testcases", methods=["GET", "POST"])
def api_testcases():
    """Retrieves or updates test cases for the assignment checker."""
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        new_tests = payload.get("tests", [])

        if not isinstance(new_tests, list) or len(new_tests) == 0:
            return jsonify({"success": False, "error": "At least one test case is required."}), 400

        validated = []
        for idx, tc in enumerate(new_tests, 1):
            inp = str(tc.get("input", "")).strip()
            exp = str(tc.get("expected", "")).strip()
            if not inp or not exp:
                return jsonify({"success": False, "error": f"Test case #{idx} missing input or expected output."}), 400
            validated.append({"id": idx, "input": inp, "expected": exp})

        if save_test_cases_to_file(validated):
            return jsonify({
                "success": True,
                "message": f"Successfully saved {len(validated)} test cases to testcases.txt.",
                "tests": validated
            })
        else:
            return jsonify({"success": False, "error": "Failed to persist testcases.txt."}), 500

    # GET request
    tests = load_test_cases_from_file()
    return jsonify(
        {
            "problem": "Maximum of Two Integers",
            "description": "Program reads two integers from standard input and prints the maximum value.",
            "tests": tests,
            "algorithms": [
                {
                    "name": "Stack-Based Bracket Check",
                    "role": "Verifies syntax balance for (), [], and {} using LIFO stack",
                },
                {
                    "name": "Hash Table Expected Lookup",
                    "role": "O(1) average retrieval of expected outputs from test inputs",
                },
                {
                    "name": "FIFO Submission Queue",
                    "role": "Initial ordered ingestion of incoming student submissions",
                },
                {
                    "name": "Max Heap Priority Queue",
                    "role": "Schedules processing order prioritized by source code size",
                },
                {
                    "name": "Tree: Simplified Block-Structure Representation",
                    "role": "Hierarchical block decomposition for {} scopes and token groups (structural representation, not a full compiler AST)",
                },
                {
                    "name": "Graph: Consecutive-Token Transition Graph",
                    "role": "Directed graph of adjacent token sequence transitions (token[i] -> token[i+1]) measuring structural adjacency (not actual runtime control flow)",
                },
                {
                    "name": "Composite Structural Similarity Formula",
                    "role": "50% Token + 25% Tree + 25% Graph. Threshold >= 70% alerts potential similarity for manual review.",
                },
            ],
            "disclaimer": "NOTE: Structural similarity metrics are indicators of textual and structural resemblance only. High similarity does not prove plagiarism or academic dishonesty."
        }
    )


@app.route("/api/testcases/reset", methods=["POST"])
def api_testcases_reset():
    """Resets test cases to the default suite."""
    if save_test_cases_to_file(DEFAULT_TESTS):
        return jsonify({
            "success": True,
            "message": "Reset test cases to default suite.",
            "tests": DEFAULT_TESTS
        })
    return jsonify({"success": False, "error": "Failed to reset test cases."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0" if (os.environ.get("RENDER") or os.environ.get("PORT")) else "127.0.0.1")
    print("=" * 60)
    print("  Intelligent Assignment Checker Dashboard")
    print(f"  Running at: http://{host}:{port}")
    print("=" * 60)
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host=host, port=port, debug=debug_mode)
