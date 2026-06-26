from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

from app.extensions import db
from app.models import DailyTask, UserProfile, WeeklyQuiz


def normalize_language(language: str | None) -> str:
    key = (language or "python").strip().lower()
    if key in {"js", "javascript", "node"}:
        return "javascript"
    if key == "cpp":
        return "c++"
    if key not in {"python", "javascript", "java", "c", "c++"}:
        return "python"
    return key


def language_label(language: str | None) -> str:
    key = normalize_language(language)
    return {
        "python": "Python",
        "javascript": "JavaScript",
        "java": "Java",
        "c": "C",
        "c++": "C++",
    }[key]


def difficulty_bonus(difficulty: str | None) -> int:
    key = (difficulty or "beginner").strip().lower()
    return {
        "beginner": 0,
        "intermediate": 5,
        "advanced": 10,
    }.get(key, 0)


LANGUAGE_BANKS: dict[str, dict] = {
    "python": {
        "code": {
            "task_key": "python-word-counter",
            "title": "Python Code Challenge: Word Counter",
            "description": "Write a program that reads one line, counts each unique word, and prints the counts in alphabetical order.",
            "starter_code": (
                "from collections import Counter\n"
                "\n"
                "def solve(text: str) -> str:\n"
                "    # TODO: split the input, count words, and format the result.\n"
                "    words = [word.lower() for word in text.split() if word.strip()]\n"
                "    counts = Counter(words)\n"
                "    return '\\n'.join(f'{word} {counts[word]}' for word in sorted(counts))\n"
                "\n"
                "if __name__ == '__main__':\n"
                "    import sys\n"
                "    data = sys.stdin.read().strip()\n"
                "    print(solve(data))\n"
            ),
            "sample_input": "apple banana apple\n",
            "expected_output": "apple 2\nbanana 1",
            "hint": "Use split, lowercase words, and a dictionary or Counter.",
            "validation_json": ["split", "lower", "count", "sorted"],
        },
        "daily_questions": [
            {
                "id": 1,
                "question": "Which structure is best for key-value storage in Python?",
                "options": ["List", "Dictionary", "Tuple", "Set"],
                "answer": "Dictionary",
            },
            {
                "id": 2,
                "question": "What does `len(['a', 'b', 'c'])` return?",
                "options": ["2", "3", "1", "Error"],
                "answer": "3",
            },
            {
                "id": 3,
                "question": "Which keyword creates a function in Python?",
                "options": ["function", "def", "lambda", "make"],
                "answer": "def",
            },
            {
                "id": 4,
                "question": "Which of these is immutable?",
                "options": ["List", "Dictionary", "Tuple", "Set"],
                "answer": "Tuple",
            },
            {
                "id": 5,
                "question": "What does slicing `text[:3]` do?",
                "options": ["Last 3 characters", "First 3 characters", "Middle 3 characters", "Reverse text"],
                "answer": "First 3 characters",
            },
        ],
        "weekly_questions": [
            {
                "id": 1,
                "question": "What is the result of `3 * 'ha'` in Python?",
                "options": ["'hahaha'", "'3ha'", "Error", "'ha3'"],
                "answer": "'hahaha'",
            },
            {
                "id": 2,
                "question": "Which method adds an item to the end of a list?",
                "options": ["append()", "push()", "insert()", "extend()"],
                "answer": "append()",
            },
            {
                "id": 3,
                "question": "What does `dict.keys()` return?",
                "options": ["A list of values", "A dict of keys", "A view of keys", "A tuple of keys"],
                "answer": "A view of keys",
            },
            {
                "id": 4,
                "question": "Which expression creates a list comprehension?",
                "options": [
                    "[x for x in range(3)]",
                    "{x for x in range(3)}",
                    "(x for x in range(3))",
                    "list(range(3))",
                ],
                "answer": "[x for x in range(3)]",
            },
            {
                "id": 5,
                "question": "What does `sorted()` return?",
                "options": ["A sorted list", "The same tuple", "A generator", "A dictionary"],
                "answer": "A sorted list",
            },
            {
                "id": 6,
                "question": "Which module helps with counting frequencies easily?",
                "options": ["math", "collections", "random", "os"],
                "answer": "collections",
            },
            {
                "id": 7,
                "question": "What is the default indexing direction in Python strings?",
                "options": ["1-based", "0-based", "Negative only", "Undefined"],
                "answer": "0-based",
            },
        ],
    },
    "javascript": {
        "code": {
            "task_key": "javascript-array-dedup",
            "title": "JavaScript Code Challenge: Remove Duplicates",
            "description": "Read a comma-separated list from stdin and print the unique values in their original order.",
            "starter_code": (
                "function solve(text) {\n"
                "  // TODO: split the input, remove duplicates, and print the unique values.\n"
                "  const values = text.split(',').map((item) => item.trim()).filter(Boolean);\n"
                "  const seen = new Set();\n"
                "  const unique = [];\n"
                "  for (const value of values) {\n"
                "    if (!seen.has(value)) {\n"
                "      seen.add(value);\n"
                "      unique.push(value);\n"
                "    }\n"
                "  }\n"
                "  return unique.join(' ');\n"
                "}\n"
                "\n"
                "const fs = require('fs');\n"
                "const input = fs.readFileSync(0, 'utf8').trim();\n"
                "console.log(solve(input));\n"
            ),
            "sample_input": "red, blue, red, green\n",
            "expected_output": "red blue green",
            "hint": "Use split, trim, and a Set to keep the first occurrence of each value.",
            "validation_json": ["split", "trim", "set", "unique"],
        },
        "daily_questions": [
            {
                "id": 1,
                "question": "Which keyword creates a block-scoped variable in JavaScript?",
                "options": ["var", "let", "both var and let", "const"],
                "answer": "let",
            },
            {
                "id": 2,
                "question": "What does `Array.prototype.map()` return?",
                "options": ["A single number", "A new array", "A boolean", "An object"],
                "answer": "A new array",
            },
            {
                "id": 3,
                "question": "Which comparison checks value and type?",
                "options": ["==", "=", "===", "!="],
                "answer": "===",
            },
            {
                "id": 4,
                "question": "Which object is commonly used for async result handling?",
                "options": ["Promise", "Number", "Date", "String"],
                "answer": "Promise",
            },
            {
                "id": 5,
                "question": "What does `console.log()` do?",
                "options": ["Reads a file", "Prints output", "Creates a variable", "Ends the program"],
                "answer": "Prints output",
            },
        ],
        "weekly_questions": [
            {
                "id": 1,
                "question": "Which method removes the last item from an array?",
                "options": ["pop()", "shift()", "push()", "slice()"],
                "answer": "pop()",
            },
            {
                "id": 2,
                "question": "What is the result of `typeof null`?",
                "options": ["null", "object", "undefined", "number"],
                "answer": "object",
            },
            {
                "id": 3,
                "question": "Which syntax defines an arrow function?",
                "options": ["function x() {}", "() => {}", "=> x()", "arrow x()"],
                "answer": "() => {}",
            },
            {
                "id": 4,
                "question": "Which operator is used for strict equality in JavaScript?",
                "options": ["==", "===", "!==", ":="],
                "answer": "===",
            },
            {
                "id": 5,
                "question": "Which method merges arrays into a new array?",
                "options": ["join()", "concat()", "slice()", "splice()"],
                "answer": "concat()",
            },
            {
                "id": 6,
                "question": "What does `JSON.parse()` do?",
                "options": ["Turns an object into JSON", "Parses JSON text into an object", "Sorts JSON keys", "Deletes JSON"],
                "answer": "Parses JSON text into an object",
            },
            {
                "id": 7,
                "question": "Which event loop concept helps with async operations?",
                "options": ["Microtasks", "Inheritance", "Hoisting", "Destructuring"],
                "answer": "Microtasks",
            },
        ],
    },
    "java": {
        "code": {
            "task_key": "java-palindrome-checker",
            "title": "Java Code Challenge: Palindrome Checker",
            "description": "Read a word from stdin and print whether it is a palindrome.",
            "starter_code": (
                "import java.util.Scanner;\n"
                "\n"
                "public class Main {\n"
                "  static boolean isPalindrome(String text) {\n"
                "    // TODO: compare characters from both ends.\n"
                "    int left = 0;\n"
                "    int right = text.length() - 1;\n"
                "    while (left < right) {\n"
                "      if (text.charAt(left) != text.charAt(right)) {\n"
                "        return false;\n"
                "      }\n"
                "      left++;\n"
                "      right--;\n"
                "    }\n"
                "    return true;\n"
                "  }\n"
                "\n"
                "  public static void main(String[] args) {\n"
                "    Scanner scanner = new Scanner(System.in);\n"
                "    String text = scanner.nextLine().trim();\n"
                "    System.out.println(isPalindrome(text));\n"
                "  }\n"
                "}\n"
            ),
            "sample_input": "level\n",
            "expected_output": "true",
            "hint": "Compare characters from both ends until they meet in the middle.",
            "validation_json": ["charAt", "scanner", "while", "boolean"],
        },
        "daily_questions": [
            {
                "id": 1,
                "question": "Which keyword defines a class member shared by all instances?",
                "options": ["final", "static", "public", "private"],
                "answer": "static",
            },
            {
                "id": 2,
                "question": "Which collection keeps elements in insertion order and allows duplicates?",
                "options": ["HashSet", "ArrayList", "TreeSet", "HashMap"],
                "answer": "ArrayList",
            },
            {
                "id": 3,
                "question": "What is the parent class of every Java class?",
                "options": ["Object", "Class", "Base", "Main"],
                "answer": "Object",
            },
            {
                "id": 4,
                "question": "Which keyword is used to inherit a class?",
                "options": ["implements", "extends", "inherits", "super"],
                "answer": "extends",
            },
            {
                "id": 5,
                "question": "Which statement handles exceptions?",
                "options": ["switch", "try-catch", "if-else", "for-each"],
                "answer": "try-catch",
            },
        ],
        "weekly_questions": [
            {
                "id": 1,
                "question": "Which interface must be implemented to run code in a separate thread?",
                "options": ["Runnable", "Comparable", "Serializable", "Iterable"],
                "answer": "Runnable",
            },
            {
                "id": 2,
                "question": "Which access modifier makes a member visible everywhere?",
                "options": ["private", "protected", "public", "default"],
                "answer": "public",
            },
            {
                "id": 3,
                "question": "What does `System.out.println()` do?",
                "options": ["Reads input", "Prints a line", "Creates a package", "Compiles code"],
                "answer": "Prints a line",
            },
            {
                "id": 4,
                "question": "Which class is commonly used for dynamic arrays?",
                "options": ["HashMap", "ArrayList", "Scanner", "Thread"],
                "answer": "ArrayList",
            },
            {
                "id": 5,
                "question": "Which keyword prevents a class from being subclassed?",
                "options": ["abstract", "final", "static", "private"],
                "answer": "final",
            },
            {
                "id": 6,
                "question": "What does `equals()` compare in Java?",
                "options": ["Memory addresses only", "Object content", "Package names", "Loop counts"],
                "answer": "Object content",
            },
            {
                "id": 7,
                "question": "Which data structure is best for fast key lookup?",
                "options": ["ArrayList", "LinkedList", "HashMap", "Stack"],
                "answer": "HashMap",
            },
        ],
    },
    "c": {
        "code": {
            "task_key": "c-vowel-counter",
            "title": "C Code Challenge: Vowel Counter",
            "description": "Read a line from stdin and count the vowels in it.",
            "starter_code": (
                "#include <stdio.h>\n"
                "#include <ctype.h>\n"
                "\n"
                "int main(void) {\n"
                "    char text[256];\n"
                "    if (!fgets(text, sizeof(text), stdin)) {\n"
                "        return 0;\n"
                "    }\n"
                "    int count = 0;\n"
                "    for (int i = 0; text[i] != '\\0'; i++) {\n"
                "        char c = (char)tolower((unsigned char)text[i]);\n"
                "        if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u') {\n"
                "            count++;\n"
                "        }\n"
                "    }\n"
                "    printf(\"%d\\n\", count);\n"
                "    return 0;\n"
                "}\n"
            ),
            "sample_input": "adaptive learning\n",
            "expected_output": "7",
            "hint": "Use fgets, tolower, and a loop over the character array.",
            "validation_json": ["fgets", "tolower", "loop", "printf"],
        },
        "daily_questions": [
            {
                "id": 1,
                "question": "Which function reads a line from stdin safely?",
                "options": ["scanf", "fgets", "gets", "puts"],
                "answer": "fgets",
            },
            {
                "id": 2,
                "question": "What is used to print formatted output in C?",
                "options": ["printf", "cin", "cout", "format"],
                "answer": "printf",
            },
            {
                "id": 3,
                "question": "What does a pointer store?",
                "options": ["A number only", "The address of a value", "A loop count", "A keyword"],
                "answer": "The address of a value",
            },
            {
                "id": 4,
                "question": "Which header provides character helpers like tolower?",
                "options": ["math.h", "ctype.h", "string.h", "stdlib.h"],
                "answer": "ctype.h",
            },
            {
                "id": 5,
                "question": "Which loop is safest when the number of iterations is known?",
                "options": ["for", "while", "do-while", "goto"],
                "answer": "for",
            },
        ],
        "weekly_questions": [
            {
                "id": 1,
                "question": "What symbol is used to dereference a pointer?",
                "options": ["&", "*", "%", "#"],
                "answer": "*",
            },
            {
                "id": 2,
                "question": "Which operator gets the address of a variable?",
                "options": ["*", "&", "->", "::"],
                "answer": "&",
            },
            {
                "id": 3,
                "question": "What does `strlen()` return?",
                "options": ["Array size in bytes", "String length without null terminator", "Pointer address", "The last character"],
                "answer": "String length without null terminator",
            },
            {
                "id": 4,
                "question": "Which function allocates memory dynamically?",
                "options": ["malloc", "printf", "scanf", "free"],
                "answer": "malloc",
            },
            {
                "id": 5,
                "question": "What does `free()` do?",
                "options": ["Creates memory", "Releases allocated memory", "Copies memory", "Prints memory"],
                "answer": "Releases allocated memory",
            },
            {
                "id": 6,
                "question": "What is the base index of a C array?",
                "options": ["0", "1", "-1", "Depends on compiler"],
                "answer": "0",
            },
            {
                "id": 7,
                "question": "Which function compares two strings?",
                "options": ["strcmp", "strcat", "strlen", "strcpy"],
                "answer": "strcmp",
            },
        ],
    },
    "c++": {
        "code": {
            "task_key": "cpp-max-finder",
            "title": "C++ Code Challenge: Max Finder",
            "description": "Read integers from stdin and print the maximum value.",
            "starter_code": (
                "#include <iostream>\n"
                "#include <vector>\n"
                "#include <algorithm>\n"
                "using namespace std;\n"
                "\n"
                "int main() {\n"
                "    vector<int> values;\n"
                "    int x;\n"
                "    while (cin >> x) {\n"
                "        values.push_back(x);\n"
                "    }\n"
                "    if (values.empty()) {\n"
                "        cout << 0 << endl;\n"
                "        return 0;\n"
                "    }\n"
                "    cout << *max_element(values.begin(), values.end()) << endl;\n"
                "    return 0;\n"
                "}\n"
            ),
            "sample_input": "4 9 2 15 7\n",
            "expected_output": "15",
            "hint": "Use a vector and std::max_element.",
            "validation_json": ["vector", "max_element", "cin", "cout"],
        },
        "daily_questions": [
            {
                "id": 1,
                "question": "Which container stores items in contiguous memory?",
                "options": ["list", "vector", "map", "set"],
                "answer": "vector",
            },
            {
                "id": 2,
                "question": "Which header gives you `cout` and `cin`?",
                "options": ["iostream", "vector", "algorithm", "cmath"],
                "answer": "iostream",
            },
            {
                "id": 3,
                "question": "Which keyword references the current object inside a class method?",
                "options": ["this", "self", "current", "me"],
                "answer": "this",
            },
            {
                "id": 4,
                "question": "What does `push_back` do to a vector?",
                "options": ["Removes the first item", "Adds an item to the end", "Sorts the vector", "Clears the vector"],
                "answer": "Adds an item to the end",
            },
            {
                "id": 5,
                "question": "Which function sorts a range?",
                "options": ["sort", "swap", "copy", "find"],
                "answer": "sort",
            },
        ],
        "weekly_questions": [
            {
                "id": 1,
                "question": "What is a reference in C++?",
                "options": ["Another name for a variable", "A pointer that cannot be changed", "A class method", "A loop type"],
                "answer": "Another name for a variable",
            },
            {
                "id": 2,
                "question": "Which operator accesses a member through a pointer?",
                "options": [".", "->", "::", "&"],
                "answer": "->",
            },
            {
                "id": 3,
                "question": "Which container keeps items sorted automatically?",
                "options": ["vector", "queue", "map", "stack"],
                "answer": "map",
            },
            {
                "id": 4,
                "question": "Which header is used for `std::sort`?",
                "options": ["algorithm", "iostream", "cstdio", "memory"],
                "answer": "algorithm",
            },
            {
                "id": 5,
                "question": "What does a constructor do?",
                "options": ["Deletes an object", "Initializes an object", "Prints output", "Sorts values"],
                "answer": "Initializes an object",
            },
            {
                "id": 6,
                "question": "What does `const` mean on a method or variable?",
                "options": ["Can never be created", "Cannot be modified", "Runs faster", "Uses dynamic memory"],
                "answer": "Cannot be modified",
            },
            {
                "id": 7,
                "question": "Which standard library feature can iterate over containers?",
                "options": ["range-based for", "goto", "switch", "typedef"],
                "answer": "range-based for",
            },
        ],
    },
}


def _copy_questions(items: list[dict]) -> list[dict]:
    return [deepcopy(item) for item in items]


def _preferred_language(profile: UserProfile | None) -> str:
    if profile and isinstance(profile.preferred_languages, list) and profile.preferred_languages:
        return normalize_language(profile.preferred_languages[0])
    return "python"


def build_daily_task_bundle(language: str | None, difficulty: str | None) -> list[dict]:
    key = normalize_language(language)
    bank = LANGUAGE_BANKS[key]
    points_bonus = difficulty_bonus(difficulty)
    label = language_label(key)

    return [
        {
            "task_type": "code",
            "title": bank["code"]["title"],
            "description": bank["code"]["description"],
            "points_reward": 30 + points_bonus,
            "content_json": {
                "mode": "code",
                "language": key,
                "language_label": label,
                "task_key": bank["code"]["task_key"],
                "starter_code": bank["code"]["starter_code"],
                "sample_input": bank["code"]["sample_input"],
                "expected_output": bank["code"]["expected_output"],
                "hint": bank["code"]["hint"],
                "validation_json": bank["code"]["validation_json"],
            },
        },
        {
            "task_type": "quiz",
            "title": f"{label} Daily Quiz: Core Concepts",
            "description": f"Answer 5 short MCQs about {label} fundamentals to lock in today's concepts.",
            "points_reward": 20 + points_bonus,
            "content_json": {
                "mode": "quiz",
                "language": key,
                "language_label": label,
                "task_key": f"{key}-daily-quiz",
                "questions": _copy_questions(bank["daily_questions"]),
            },
        },
    ]


def build_weekly_quiz_bundle(language: str | None, difficulty: str | None) -> dict:
    key = normalize_language(language)
    bank = LANGUAGE_BANKS[key]
    label = language_label(key)
    points_bonus = difficulty_bonus(difficulty)

    questions = _copy_questions(bank["weekly_questions"])
    return {
        "title": f"Weekly Quiz: {label} Deep Dive",
        "difficulty": (difficulty or "beginner").strip().lower() or "beginner",
        "questions": questions[:7],
        "points_reward": 100 + (points_bonus * 2),
        "language": key,
        "language_label": label,
        "week_topic": f"{label} Core Concepts",
        "task_key": f"{key}-weekly-quiz",
    }


def ensure_daily_and_weekly_progression(user_id: int, profile: UserProfile, today: date) -> None:
    language = _preferred_language(profile)
    if not language:
        return
    difficulty = profile.difficulty_level or "beginner"
    daily_rows = DailyTask.query.filter_by(user_id=user_id, due_date=today).all()
    if not daily_rows:
        for item in build_daily_task_bundle(language, difficulty):
            db.session.add(
                DailyTask(
                    user_id=user_id,
                    title=item["title"],
                    description=item["description"],
                    task_type=item["task_type"],
                    difficulty=profile.difficulty_level or "beginner",
                    status="assigned",
                    points_reward=item["points_reward"],
                    content_json=item["content_json"],
                    due_date=today,
                )
            )
    else:
        desired_bundle = build_daily_task_bundle(language, difficulty)
        for index, row in enumerate(daily_rows):
            desired = desired_bundle[min(len(desired_bundle) - 1, index)]
            if not desired:
                continue
            payload = row.content_json or {}
            should_backfill = (
                not isinstance(payload, dict)
                or payload.get("mode") != desired["content_json"].get("mode")
                or not payload
                or row.task_type not in {"code", "quiz"}
            )
            if should_backfill:
                row.title = desired["title"]
                row.description = desired["description"]
                row.task_type = desired["task_type"]
                row.difficulty = difficulty
                row.points_reward = desired["points_reward"]
                row.content_json = deepcopy(desired["content_json"])

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    quiz = WeeklyQuiz.query.filter_by(user_id=user_id, week_start=week_start).first()
    if not quiz:
        bundle = build_weekly_quiz_bundle(language, difficulty)
        db.session.add(
            WeeklyQuiz(
                user_id=user_id,
                title=f"{bundle['title']} ({week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d})",
                week_start=week_start,
                week_end=week_end,
                difficulty=bundle["difficulty"],
                question_payload=bundle["questions"],
            )
        )
    else:
        bundle = build_weekly_quiz_bundle(language, difficulty)
        payload = quiz.question_payload or []
        if (
            not isinstance(payload, list)
            or len(payload) < len(bundle["questions"])
            or quiz.title != f"{bundle['title']} ({week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d})"
        ):
            quiz.title = f"{bundle['title']} ({week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d})"
            quiz.week_end = week_end
            quiz.difficulty = bundle["difficulty"]
            quiz.question_payload = bundle["questions"]
