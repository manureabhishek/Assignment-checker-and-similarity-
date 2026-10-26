#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <cctype>
#include <cstdlib>

using namespace std;

// =====================================================
// 1. STACK - BRACKET CHECKING
// =====================================================

class Stack {
private:
    vector<char> data;

public:
    void push(char value) {
        data.push_back(value);
    }

    void pop() {
        if (!data.empty()) data.pop_back();
    }

    char top() const {
        return data.empty() ? '\0' : data.back();
    }

    bool empty() const {
        return data.empty();
    }
};

bool bracketsBalanced(const vector<string>& tokens) {
    Stack st;

    for (size_t i = 0; i < tokens.size(); i++) {
        string t = tokens[i];

        if (t == "(" || t == "[" || t == "{") {
            st.push(t[0]);
        }
        else if (t == ")" || t == "]" || t == "}") {
            if (st.empty()) return false;

            char opening = st.top();
            st.pop();

            if ((t == ")" && opening != '(') ||
                (t == "]" && opening != '[') ||
                (t == "}" && opening != '{')) {
                return false;
            }
        }
    }

    return st.empty();
}

// =====================================================
// 2. FILE HANDLING
// =====================================================

string readFile(const string& path) {
    ifstream file(path.c_str());

    if (!file.is_open()) return "";

    stringstream buffer;
    buffer << file.rdbuf();

    return buffer.str();
}

string removeComments(const string& code) {
    string result;

    bool lineComment = false;
    bool blockComment = false;
    bool inString = false;
    bool inChar = false;
    bool escape = false;

    for (size_t i = 0; i < code.size(); i++) {
        char c = code[i];
        char next = (i + 1 < code.size()) ? code[i + 1] : '\0';

        if (lineComment) {
            if (c == '\n') {
                lineComment = false;
                result += '\n';
            }
            continue;
        }

        if (blockComment) {
            if (c == '*' && next == '/') {
                blockComment = false;
                i++;
            }
            else if (c == '\n') {
                result += '\n';
            }
            continue;
        }

        if (!inString && !inChar && c == '/' && next == '/') {
            lineComment = true;
            i++;
            continue;
        }

        if (!inString && !inChar && c == '/' && next == '*') {
            blockComment = true;
            i++;
            continue;
        }

        result += c;

        if (escape) {
            escape = false;
            continue;
        }

        if ((inString || inChar) && c == '\\') {
            escape = true;
            continue;
        }

        if (!inChar && c == '"') {
            inString = !inString;
        }
        else if (!inString && c == '\'') {
            inChar = !inChar;
        }
    }

    return result;
}

// =====================================================
// 3. TOKENIZATION
// =====================================================

bool isIdentifierStart(char c) {
    return isalpha(static_cast<unsigned char>(c)) || c == '_';
}

bool isIdentifierPart(char c) {
    return isalnum(static_cast<unsigned char>(c)) || c == '_';
}

vector<string> tokenize(const string& code) {
    vector<string> tokens;
    size_t i = 0;

    while (i < code.size()) {
        char c = code[i];

        if (isspace(static_cast<unsigned char>(c))) {
            i++;
            continue;
        }

        if (isIdentifierStart(c)) {
            string token;

            while (i < code.size() && isIdentifierPart(code[i])) {
                token += code[i++];
            }

            tokens.push_back(token);
        }
        else if (isdigit(static_cast<unsigned char>(c))) {
            string token;

            while (i < code.size() &&
                   (isalnum(static_cast<unsigned char>(code[i])) ||
                    code[i] == '.')) {
                token += code[i++];
            }

            tokens.push_back(token);
        }
        else if (c == '"') {
            string token;
            token += code[i++];

            bool escaped = false;

            while (i < code.size()) {
                char current = code[i++];
                token += current;

                if (escaped) {
                    escaped = false;
                }
                else if (current == '\\') {
                    escaped = true;
                }
                else if (current == '"') {
                    break;
                }
            }

            tokens.push_back(token);
        }
        else if (c == '\'') {
            string token;
            token += code[i++];

            bool escaped = false;

            while (i < code.size()) {
                char current = code[i++];
                token += current;

                if (escaped) {
                    escaped = false;
                }
                else if (current == '\\') {
                    escaped = true;
                }
                else if (current == '\'') {
                    break;
                }
            }

            tokens.push_back(token);
        }
        else {
            string two;

            if (i + 1 < code.size()) {
                two = code.substr(i, 2);
            }

            if (two == "==" || two == "!=" ||
                two == "<=" || two == ">=" ||
                two == "++" || two == "--" ||
                two == "&&" || two == "||" ||
                two == "+=" || two == "-=" ||
                two == "*=" || two == "/=" ||
                two == "->" || two == "::" ||
                two == "<<" || two == ">>" ||
                two == "%=" || two == "&=" ||
                two == "|=" || two == "^=") {
                tokens.push_back(two);
                i += 2;
            }
            else {
                tokens.push_back(string(1, code[i]));
                i++;
            }
        }
    }

    return tokens;
}

// =====================================================
// 4. OUTPUT COMPARISON
// =====================================================

vector<string> tokenizeOutput(const string& output) {
    vector<string> tokens;
    stringstream ss(output);
    string token;

    while (ss >> token) {
        tokens.push_back(token);
    }

    return tokens;
}

bool outputsMatch(const string& actual, const string& expected) {
    return tokenizeOutput(actual) == tokenizeOutput(expected);
}

// =====================================================
// 5. HASH TABLE - EXPECTED OUTPUT LOOKUP
// =====================================================

class HashTable {
private:
    static const int SIZE = 101;

    vector<vector<pair<string, string> > > table;

    int hashFunction(const string& key) const {
        unsigned long hash = 0;

        for (size_t i = 0; i < key.size(); i++) {
            hash = (hash * 31 +
                    static_cast<unsigned char>(key[i])) % SIZE;
        }

        return static_cast<int>(hash);
    }

public:
    HashTable() {
        table.resize(SIZE);
    }

    void insert(const string& key, const string& value) {
        int index = hashFunction(key);

        for (size_t i = 0; i < table[index].size(); i++) {
            if (table[index][i].first == key) {
                table[index][i].second = value;
                return;
            }
        }

        table[index].push_back(make_pair(key, value));
    }

    bool search(const string& key, string& value) const {
        int index = hashFunction(key);

        for (size_t i = 0; i < table[index].size(); i++) {
            if (table[index][i].first == key) {
                value = table[index][i].second;
                return true;
            }
        }

        return false;
    }
};

// =====================================================
// 6. PRIORITY QUEUE - MAX HEAP
// =====================================================

struct QueueItem {
    string filename;
    int priority;
};

class PriorityQueue {
private:
    vector<QueueItem> heap;

    void heapifyUp(int index) {
        while (index > 0) {
            int parent = (index - 1) / 2;

            if (heap[parent].priority >= heap[index].priority) {
                break;
            }

            swap(heap[parent], heap[index]);
            index = parent;
        }
    }

    void heapifyDown(int index) {
        int size = static_cast<int>(heap.size());

        while (true) {
            int largest = index;
            int left = 2 * index + 1;
            int right = 2 * index + 2;

            if (left < size &&
                heap[left].priority > heap[largest].priority) {
                largest = left;
            }

            if (right < size &&
                heap[right].priority > heap[largest].priority) {
                largest = right;
            }

            if (largest == index) break;

            swap(heap[index], heap[largest]);
            index = largest;
        }
    }

public:
    void enqueue(const string& filename, int priority) {
        QueueItem item;
        item.filename = filename;
        item.priority = priority;

        heap.push_back(item);
        heapifyUp(static_cast<int>(heap.size()) - 1);
    }

    bool dequeue(QueueItem& result) {
        if (heap.empty()) return false;

        result = heap[0];

        heap[0] = heap.back();
        heap.pop_back();

        if (!heap.empty()) {
            heapifyDown(0);
        }

        return true;
    }

    bool empty() const {
        return heap.empty();
    }
};

// =====================================================
// 7. FIFO SUBMISSION QUEUE
// =====================================================

class SubmissionQueue {
private:
    vector<string> items;
    size_t frontIndex;

public:
    SubmissionQueue() : frontIndex(0) {}

    void enqueue(const string& filename) {
        items.push_back(filename);
    }

    bool dequeue(string& filename) {
        if (frontIndex >= items.size()) {
            return false;
        }

        filename = items[frontIndex];
        frontIndex++;

        return true;
    }

    bool empty() const {
        return frontIndex >= items.size();
    }
};

// =====================================================
// 8. TREE - SIMPLIFIED CODE STRUCTURE
// =====================================================

struct TreeNode {
    string value;
    vector<TreeNode*> children;

    TreeNode(const string& v) {
        value = v;
    }
};

TreeNode* buildTree(const vector<string>& tokens) {
    TreeNode* root = new TreeNode("ROOT");

    vector<TreeNode*> parents;
    parents.push_back(root);

    for (size_t i = 0; i < tokens.size(); i++) {
        const string& token = tokens[i];

        if (token == "}") {
            if (parents.size() > 1) {
                parents.pop_back();
            }

            TreeNode* node = new TreeNode("}");
            parents.back()->children.push_back(node);
        }
        else if (token == "{") {
            TreeNode* node = new TreeNode("BLOCK");

            parents.back()->children.push_back(node);
            parents.push_back(node);
        }
        else {
            TreeNode* node = new TreeNode(token);
            parents.back()->children.push_back(node);
        }
    }

    return root;
}

void collectTreeFeatures(TreeNode* node, vector<string>& features) {
    if (node == NULL) return;

    features.push_back(node->value);

    for (size_t i = 0; i < node->children.size(); i++) {
        collectTreeFeatures(node->children[i], features);
    }
}

void deleteTree(TreeNode* node) {
    if (node == NULL) return;

    for (size_t i = 0; i < node->children.size(); i++) {
        deleteTree(node->children[i]);
    }

    delete node;
}

// =====================================================
// 9. GRAPH - TOKEN FLOW REPRESENTATION
// =====================================================

class Graph {
public:
    vector<pair<string, string> > edges;

    void addEdge(const string& from, const string& to) {
        edges.push_back(make_pair(from, to));
    }
};

Graph buildGraph(const vector<string>& tokens) {
    Graph graph;

    for (size_t i = 0; i + 1 < tokens.size(); i++) {
        graph.addEdge(tokens[i], tokens[i + 1]);
    }

    return graph;
}

vector<string> graphFeatures(const Graph& graph) {
    vector<string> features;

    for (size_t i = 0; i < graph.edges.size(); i++) {
        features.push_back(
            graph.edges[i].first + "->" + graph.edges[i].second
        );
    }

    return features;
}

// =====================================================
// 10. SIMILARITY CALCULATION
// =====================================================

double multisetSimilarity(const vector<string>& a,
                          const vector<string>& b) {
    if (a.empty() && b.empty()) return 100.0;
    if (a.empty() || b.empty()) return 0.0;

    map<string, int> countA;
    map<string, int> countB;

    for (size_t i = 0; i < a.size(); i++) {
        countA[a[i]]++;
    }

    for (size_t i = 0; i < b.size(); i++) {
        countB[b[i]]++;
    }

    int common = 0;

    for (map<string, int>::const_iterator it = countA.begin();
         it != countA.end(); ++it) {

        map<string, int>::const_iterator found = countB.find(it->first);

        if (found != countB.end()) {
            common += min(it->second, found->second);
        }
    }

    double total = static_cast<double>(a.size() + b.size());

    return (2.0 * common / total) * 100.0;
}

double graphSimilarity(const vector<string>& a,
                       const vector<string>& b) {
    if (a.empty() && b.empty()) return 100.0;
    if (a.empty() || b.empty()) return 0.0;

    map<string, int> setA;
    map<string, int> setB;

    for (size_t i = 0; i < a.size(); i++) {
        setA[a[i]] = 1;
    }

    for (size_t i = 0; i < b.size(); i++) {
        setB[b[i]] = 1;
    }

    int common = 0;

    for (map<string, int>::const_iterator it = setA.begin();
         it != setA.end(); ++it) {

        if (setB.find(it->first) != setB.end()) {
            common++;
        }
    }

    int total = static_cast<int>(setA.size() + setB.size()) - common;

    if (total == 0) return 100.0;

    return (100.0 * common) / total;
}

// =====================================================
// 11. SUBMISSION STRUCTURES
// =====================================================

struct TestRunDetail {
    int testIndex;
    string input;
    string expected;
    string actual;
    bool passed;
};

struct Submission {
    string filename;
    vector<string> tokens;
    vector<string> treeFeatures;
    vector<string> graphFeatures;

    double correctness;
    int passed;
    int totalTests;

    bool compiled;
    bool balanced;
    string compileError;
    vector<TestRunDetail> testDetails;
};

struct SimilarityResult {
    double token;
    double tree;
    double graph;
    double overall;
};

SimilarityResult compareSubmissions(const Submission& a,
                                    const Submission& b) {
    SimilarityResult result;

    result.token = multisetSimilarity(a.tokens, b.tokens);
    result.tree = multisetSimilarity(a.treeFeatures, b.treeFeatures);
    result.graph = graphSimilarity(a.graphFeatures, b.graphFeatures);

    result.overall = 0.50 * result.token +
                     0.25 * result.tree +
                     0.25 * result.graph;

    return result;
}

// =====================================================
// 12. TEST CASES AND COMMAND EXECUTION
// =====================================================

struct TestCase {
    string input;
    string expected;
};

bool runCommand(const string& command) {
    int result = system(command.c_str());
    return result == 0;
}

// =====================================================
// 13. MAIN FUNCTION
// =====================================================

int main() {
    cout << "==========================================" << endl;
    cout << "   INTELLIGENT ASSIGNMENT CHECKER - C++" << endl;
    cout << "==========================================" << endl;

#ifdef _WIN32
    system("mkdir reports 2>nul");
    system("dir /b submissions\\*.cpp > filelist.txt 2>nul");
    string pathSep = "\\";
    string execPrefix = ".\\";
    string exeExt = ".exe";
#else
    system("mkdir -p reports 2>/dev/null");
    // Generate filelist.txt on Linux/POSIX if not already populated
    ifstream checkList("filelist.txt");
    if (!checkList.is_open() || checkList.peek() == ifstream::traits_type::eof()) {
        system("ls -1 submissions/*.cpp 2>/dev/null | sed 's|.*/||' > filelist.txt 2>/dev/null || ls -1 submissions/*.cpp > filelist.txt 2>/dev/null");
    }
    if (checkList.is_open()) checkList.close();
    string pathSep = "/";
    string execPrefix = "./";
    string exeExt = "";
#endif

    ifstream listFile("filelist.txt");

    if (!listFile.is_open()) {
        cout << "Could not open filelist.txt" << endl;
        return 1;
    }

    SubmissionQueue submissionQueue;
    string filename;

    while (getline(listFile, filename)) {
        if (!filename.empty() && filename[filename.size() - 1] == '\r') {
            filename.erase(filename.size() - 1);
        }

        // Clean directory prefix if present in filelist (e.g. submissions/ or submissions\)
        size_t lastSlash = filename.find_last_of("/\\");
        if (lastSlash != string::npos) {
            filename = filename.substr(lastSlash + 1);
        }

        if (!filename.empty()) {
            submissionQueue.enqueue(filename);
        }
    }

    listFile.close();

    vector<string> files;
    string queuedFile;

    while (submissionQueue.dequeue(queuedFile)) {
        files.push_back(queuedFile);
    }

    if (files.empty()) {
        cout << "No .cpp files found in submissions folder." << endl;
        cout << "Please add student .cpp files inside submissions folder."
             << endl;
        return 0;
    }

    // Test cases for maximum of two integers
    vector<TestCase> tests;

    ifstream tcFile("testcases.txt");
    if (tcFile.is_open()) {
        string tcLine;
        while (getline(tcFile, tcLine)) {
            if (!tcLine.empty() && tcLine[tcLine.size() - 1] == '\r') {
                tcLine.erase(tcLine.size() - 1);
            }
            if (tcLine.empty() || tcLine[0] == '#') continue;
            size_t sep = tcLine.find("|||");
            if (sep != string::npos) {
                TestCase tc;
                tc.input = tcLine.substr(0, sep);
                if (tc.input.empty() || tc.input[tc.input.size() - 1] != '\n') {
                    tc.input += "\n";
                }
                tc.expected = tcLine.substr(sep + 3);
                tests.push_back(tc);
            }
        }
        tcFile.close();
    }

    if (tests.empty()) {
        TestCase t1;
        t1.input = "3 5\n";
        t1.expected = "5";
        tests.push_back(t1);

        TestCase t2;
        t2.input = "9 2\n";
        t2.expected = "9";
        tests.push_back(t2);

        TestCase t3;
        t3.input = "-4 7\n";
        t3.expected = "7";
        tests.push_back(t3);
    }

    // Hash Table for expected output
    HashTable expectedTable;

    for (size_t i = 0; i < tests.size(); i++) {
        expectedTable.insert(tests[i].input, tests[i].expected);
    }

    // Priority Queue
    PriorityQueue priorityQueue;

    cout << "\nPRIORITY QUEUE (MAX HEAP)" << endl;

    for (size_t i = 0; i < files.size(); i++) {
        string path = "submissions" + pathSep + files[i];
        string source = readFile(path);

        int priority = static_cast<int>(source.size());

        priorityQueue.enqueue(files[i], priority);

        cout << files[i] << " | Priority: " << priority << endl;
    }

    // Get processing order from Max Heap
    vector<QueueItem> processingOrder;
    QueueItem item;

    while (priorityQueue.dequeue(item)) {
        processingOrder.push_back(item);
    }

    cout << "\nSUBMISSION PROCESSING" << endl;

    vector<Submission> submissions;

    for (size_t i = 0; i < processingOrder.size(); i++) {
        string currentFile = processingOrder[i].filename;
        string sourcePath = "submissions" + pathSep + currentFile;

        cout << "\nProcessing: " << currentFile << endl;

        string originalCode = readFile(sourcePath);

        if (originalCode.empty()) {
            cout << "Could not read this file. Skipping." << endl;
            continue;
        }

        // Preprocessing
        string cleanCode = removeComments(originalCode);
        vector<string> tokens = tokenize(cleanCode);

        // Stack-based bracket checking
        bool balanced = bracketsBalanced(tokens);

        cout << "Tokens found: " << tokens.size() << endl;
        cout << "Bracket check: "
             << (balanced ? "Balanced" : "Not balanced") << endl;

        // Tree construction
        TreeNode* root = buildTree(tokens);

        vector<string> treeData;
        collectTreeFeatures(root, treeData);

        deleteTree(root);

        // Graph construction
        Graph graph = buildGraph(tokens);
        vector<string> graphData = graphFeatures(graph);

        // Compile student program
        string executable =
            "student_program_" + to_string(i + 1) + exeExt;

        string compileCommand =
            "g++ -std=c++11 \"" + sourcePath +
            "\" -o \"" + executable +
            "\" 2> compile_error.txt";

        bool compiled = runCommand(compileCommand);

        int passed = 0;
        int total = static_cast<int>(tests.size());
        vector<TestRunDetail> currentTestDetails;
        string currentCompileError = "";

        if (compiled) {
            cout << "Compilation: Successful" << endl;

            for (size_t testIndex = 0;
                 testIndex < tests.size(); testIndex++) {

                string inputPath = "test_input.txt";
                string outputPath = "actual_output.txt";

                ofstream inputFile(inputPath.c_str());
                inputFile << tests[testIndex].input;
                inputFile.close();

                string runCommandText =
                    execPrefix + executable +
                    " < \"" + inputPath +
                    "\" > \"" + outputPath + "\"";

                bool ran = runCommand(runCommandText);

                string actual = "";

                if (ran) {
                    actual = readFile(outputPath);
                }

                string expected;
                bool found = expectedTable.search(
                    tests[testIndex].input, expected
                );

                bool testPassed = (ran && found && outputsMatch(actual, expected));

                TestRunDetail trd;
                trd.testIndex = static_cast<int>(testIndex + 1);
                string cleanIn = tests[testIndex].input;
                while (!cleanIn.empty() && (cleanIn[cleanIn.size() - 1] == '\n' || cleanIn[cleanIn.size() - 1] == '\r')) {
                    cleanIn.erase(cleanIn.size() - 1);
                }
                trd.input = cleanIn;
                trd.expected = expected;

                string cleanAct = actual;
                while (!cleanAct.empty() && (cleanAct[cleanAct.size() - 1] == '\n' || cleanAct[cleanAct.size() - 1] == '\r')) {
                    cleanAct.erase(cleanAct.size() - 1);
                }
                trd.actual = cleanAct;
                trd.passed = testPassed;
                currentTestDetails.push_back(trd);

                if (testPassed) {
                    passed++;
                    cout << "Test " << (testIndex + 1) << ": PASS" << endl;
                }
                else {
                    cout << "Test " << (testIndex + 1) << ": FAIL" << endl;
                    cout << "Expected: " << expected << endl;
                    cout << "Actual:   " << actual << endl;
                }
            }
        }
        else {
            cout << "Compilation: Failed" << endl;
            currentCompileError = readFile("compile_error.txt");
            cout << "Check compile_error.txt for details." << endl;
        }

        double correctness = 0.0;

        if (total > 0) {
            correctness = (100.0 * passed) / total;
        }

        cout << "Test Result: " << passed << "/" << total << endl;
        cout << "Correctness: " << correctness << "%" << endl;

        Submission submission;

        submission.filename = currentFile;
        submission.tokens = tokens;
        submission.treeFeatures = treeData;
        submission.graphFeatures = graphData;
        submission.correctness = correctness;
        submission.passed = passed;
        submission.totalTests = total;
        submission.compiled = compiled;
        submission.balanced = balanced;
        submission.compileError = currentCompileError;
        submission.testDetails = currentTestDetails;

        submissions.push_back(submission);
    }

    // =================================================
    // 14. PAIRWISE SIMILARITY CHECK
    // =================================================

    cout << "\n==========================================" << endl;
    cout << "        STRUCTURAL SIMILARITY REPORT" << endl;
    cout << "==========================================" << endl;

    ofstream report("reports/final_report.txt");

    if (!report.is_open()) {
        cout << "Could not create reports/final_report.txt" << endl;
        return 1;
    }

    report << "INTELLIGENT ASSIGNMENT CHECKER - FINAL REPORT\n";
    report << "==============================================\n\n";

    report << "SUBMISSION RESULTS\n";
    report << "------------------\n";

    for (size_t i = 0; i < submissions.size(); i++) {
        cout << "\n" << submissions[i].filename << endl;
        cout << "Correctness: "
             << submissions[i].correctness << "%" << endl;

        report << "\nFile: " << submissions[i].filename << "\n";

        report << "Compilation: "
               << (submissions[i].compiled ? "Successful" : "Failed")
               << "\n";

        report << "Bracket Check: "
               << (submissions[i].balanced ? "Balanced" : "Not balanced")
               << "\n";

        report << "Tests Passed: "
               << submissions[i].passed << "/"
               << submissions[i].totalTests << "\n";

        report << "Correctness: "
               << submissions[i].correctness << "%\n";

        if (!submissions[i].compiled && !submissions[i].compileError.empty()) {
            report << "Compile Error:\n" << submissions[i].compileError << "\n";
        }

        if (submissions[i].compiled && !submissions[i].testDetails.empty()) {
            report << "Test Details:\n";
            for (size_t td = 0; td < submissions[i].testDetails.size(); td++) {
                report << "  Test " << submissions[i].testDetails[td].testIndex << ": "
                       << (submissions[i].testDetails[td].passed ? "PASS" : "FAIL")
                       << " | Input: [" << submissions[i].testDetails[td].input
                       << "] | Expected: [" << submissions[i].testDetails[td].expected
                       << "] | Actual: [" << submissions[i].testDetails[td].actual << "]\n";
            }
        }
    }

    report << "\nPAIRWISE SIMILARITY\n";
    report << "-------------------\n";

    if (submissions.size() < 2) {
        cout << "\nPairwise comparison needs at least two submissions."
             << endl;

        report << "\nOnly one submission found; pairwise comparison unavailable.\n";
    }

    for (size_t i = 0; i < submissions.size(); i++) {
        for (size_t j = i + 1; j < submissions.size(); j++) {
            SimilarityResult result =
                compareSubmissions(submissions[i], submissions[j]);

            cout << "\nComparing "
                 << submissions[i].filename
                 << " and "
                 << submissions[j].filename << endl;

            cout << "Token Similarity: "
                 << result.token << "%" << endl;

            cout << "Tree Similarity: "
                 << result.tree << "%" << endl;

            cout << "Graph Similarity: "
                 << result.graph << "%" << endl;

            cout << "Overall Similarity: "
                 << result.overall << "%" << endl;

            string status;

            if (result.overall >= 70.0) {
                status = "Potentially Similar";
            }
            else {
                status = "No High Similarity Detected";
            }

            cout << "Status: " << status << endl;

            report << "\n" << submissions[i].filename
                   << " vs " << submissions[j].filename << "\n";

            report << "Token Similarity: "
                   << result.token << "%\n";

            report << "Tree Similarity: "
                   << result.tree << "%\n";

            report << "Graph Similarity: "
                   << result.graph << "%\n";

            report << "Overall Similarity: "
                   << result.overall << "%\n";

            report << "Status: " << status << "\n";
        }
    }

    report << "\nNOTE: Similarity is an indicator only; it does not prove plagiarism.\n";
    report << "This is a simplified academic prototype.\n";

    report.close();

    cout << "\n==========================================" << endl;
    cout << "Report saved at: reports\\final_report.txt" << endl;
    cout << "==========================================" << endl;

    return 0;
} 