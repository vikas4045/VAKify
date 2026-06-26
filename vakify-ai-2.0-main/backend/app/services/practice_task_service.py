import os

from app.services.openai_service import chatgpt_json


SUPPORTED_PRACTICE_LANGUAGES = {"python", "javascript", "java", "c", "c++"}


def _normalize_language(language: str | None) -> str:
    key = (language or "python").strip().lower()
    if key in {"js", "node"}:
        return "javascript"
    if key in {"cpp"}:
        return "c++"
    if key not in SUPPORTED_PRACTICE_LANGUAGES:
        return "python"
    return key


def _language_display(language: str | None) -> str:
    return {
        "python": "Python",
        "javascript": "JavaScript",
        "java": "Java",
        "c": "C",
        "c++": "C++",
    }[_normalize_language(language)]


def _allow_practice_fallback() -> bool:
    return os.getenv("ALLOW_PRACTICE_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}


DEFAULT_TASKS = [
    {
        "task_name": "Try-catch for divide by zero",
        "description": "Handle ArithmeticException and print a user-friendly message.",
        "starter_code": (
            "public class Main {\n"
            "  public static void main(String[] args) {\n"
            "    try {\n"
            "      int result = 20 / 0;\n"
            "      System.out.println(result);\n"
            "    } catch (ArithmeticException e) {\n"
            "      System.out.println(\"Handled: \" + e.getMessage());\n"
            "    } finally {\n"
            "      System.out.println(\"Complete\");\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
    {
        "task_name": "Handle multiple exceptions",
        "description": "Use separate catch blocks for ArithmeticException and NullPointerException.",
        "starter_code": (
            "public class Main {\n"
            "  public static void main(String[] args) {\n"
            "    try {\n"
            "      String value = null;\n"
            "      System.out.println(value.length());\n"
            "    } catch (NullPointerException e) {\n"
            "      System.out.println(\"Null handled\");\n"
            "    } catch (ArithmeticException e) {\n"
            "      System.out.println(\"Math handled\");\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
    {
        "task_name": "finally block cleanup",
        "description": "Ensure finally block runs whether exception occurs or not.",
        "starter_code": (
            "public class Main {\n"
            "  public static void main(String[] args) {\n"
            "    try {\n"
            "      System.out.println(\"Run task\");\n"
            "    } finally {\n"
            "      System.out.println(\"Cleanup always runs\");\n"
            "    }\n"
            "  }\n"
            "}"
        ),
    },
]

TOPIC_TASK_BANK = {
    "Java Exception Basics": DEFAULT_TASKS,
    "Java Basics (Variables & Operators)": [
        {
            "task_name": "Variables and arithmetic",
            "description": "Declare variables, do basic arithmetic, and print a formatted output line.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    int a = 12;\n"
                "    int b = 5;\n"
                "    int sum = a + b;\n"
                "    int product = a * b;\n"
                "    System.out.println(\"sum=\" + sum + \", product=\" + product);\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Parse command-line args",
            "description": "Parse two integers from args safely and handle NumberFormatException.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try {\n"
                "      int x = Integer.parseInt(args.length > 0 ? args[0] : \"10\");\n"
                "      int y = Integer.parseInt(args.length > 1 ? args[1] : \"20\");\n"
                "      System.out.println(\"x+y=\" + (x + y));\n"
                "    } catch (NumberFormatException e) {\n"
                "      System.out.println(\"Invalid number: \" + e.getMessage());\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Type casting and precision",
            "description": "Show integer vs double division and format the output clearly.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    int a = 7;\n"
                "    int b = 2;\n"
                "    System.out.println(\"int division=\" + (a / b));\n"
                "    System.out.println(\"double division=\" + ((double) a / b));\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Control Flow (if/switch/loops)": [
        {
            "task_name": "FizzBuzz loop",
            "description": "Print numbers 1..30. For multiples of 3 print Fizz, for 5 print Buzz, for both print FizzBuzz.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    for (int i = 1; i <= 30; i++) {\n"
                "      if (i % 15 == 0) System.out.println(\"FizzBuzz\");\n"
                "      else if (i % 3 == 0) System.out.println(\"Fizz\");\n"
                "      else if (i % 5 == 0) System.out.println(\"Buzz\");\n"
                "      else System.out.println(i);\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Prime check",
            "description": "Check if a number is prime using a loop and print true/false.",
            "starter_code": (
                "public class Main {\n"
                "  static boolean isPrime(int n) {\n"
                "    if (n <= 1) return false;\n"
                "    for (int i = 2; i * i <= n; i++) {\n"
                "      if (n % i == 0) return false;\n"
                "    }\n"
                "    return true;\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    int n = 29;\n"
                "    System.out.println(isPrime(n));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Switch statement mapping",
            "description": "Use switch to map day number (1..7) to name. Print Unknown for invalid.",
            "starter_code": (
                "public class Main {\n"
                "  static String dayName(int d) {\n"
                "    switch (d) {\n"
                "      case 1: return \"Mon\";\n"
                "      case 2: return \"Tue\";\n"
                "      case 3: return \"Wed\";\n"
                "      case 4: return \"Thu\";\n"
                "      case 5: return \"Fri\";\n"
                "      case 6: return \"Sat\";\n"
                "      case 7: return \"Sun\";\n"
                "      default: return \"Unknown\";\n"
                "    }\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    System.out.println(dayName(5));\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Arrays & Strings": [
        {
            "task_name": "Max in array",
            "description": "Find and print the maximum value in an integer array.",
            "starter_code": (
                "public class Main {\n"
                "  static int max(int[] a) {\n"
                "    int m = a[0];\n"
                "    for (int v : a) if (v > m) m = v;\n"
                "    return m;\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    int[] a = {3, 9, 2, 11, 5};\n"
                "    System.out.println(max(a));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Reverse a string",
            "description": "Reverse a string using a loop and print the reversed text.",
            "starter_code": (
                "public class Main {\n"
                "  static String reverse(String s) {\n"
                "    StringBuilder sb = new StringBuilder();\n"
                "    for (int i = s.length() - 1; i >= 0; i--) sb.append(s.charAt(i));\n"
                "    return sb.toString();\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    System.out.println(reverse(\"adaptive\"));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Count vowels",
            "description": "Count vowels in a string and print the total.",
            "starter_code": (
                "public class Main {\n"
                "  static int countVowels(String s) {\n"
                "    int count = 0;\n"
                "    String t = s.toLowerCase();\n"
                "    for (int i = 0; i < t.length(); i++) {\n"
                "      char c = t.charAt(i);\n"
                "      if (c=='a'||c=='e'||c=='i'||c=='o'||c=='u') count++;\n"
                "    }\n"
                "    return count;\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    System.out.println(countVowels(\"Exception Handling\"));\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Methods & Recursion": [
        {
            "task_name": "Factorial recursion",
            "description": "Compute factorial of n using recursion and print result.",
            "starter_code": (
                "public class Main {\n"
                "  static long fact(int n) {\n"
                "    if (n <= 1) return 1;\n"
                "    return n * fact(n - 1);\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    System.out.println(fact(6));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "GCD method",
            "description": "Implement Euclid's algorithm for GCD and print gcd(48,18).",
            "starter_code": (
                "public class Main {\n"
                "  static int gcd(int a, int b) {\n"
                "    while (b != 0) {\n"
                "      int t = a % b;\n"
                "      a = b;\n"
                "      b = t;\n"
                "    }\n"
                "    return a;\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    System.out.println(gcd(48, 18));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Palindrome check",
            "description": "Create a method that checks palindrome and prints true/false.",
            "starter_code": (
                "public class Main {\n"
                "  static boolean isPalindrome(String s) {\n"
                "    int i = 0, j = s.length() - 1;\n"
                "    while (i < j) {\n"
                "      if (s.charAt(i) != s.charAt(j)) return false;\n"
                "      i++; j--;\n"
                "    }\n"
                "    return true;\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    System.out.println(isPalindrome(\"level\"));\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "OOP: Classes & Objects": [
        {
            "task_name": "Create a Student class",
            "description": "Create a Student class with name/marks and a method to return grade.",
            "starter_code": (
                "class Student {\n"
                "  String name;\n"
                "  int marks;\n"
                "  Student(String name, int marks) { this.name = name; this.marks = marks; }\n"
                "  String grade() {\n"
                "    if (marks >= 90) return \"A\";\n"
                "    if (marks >= 75) return \"B\";\n"
                "    if (marks >= 60) return \"C\";\n"
                "    return \"D\";\n"
                "  }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    Student s = new Student(\"Ravi\", 82);\n"
                "    System.out.println(s.name + \" grade=\" + s.grade());\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Encapsulation with getters/setters",
            "description": "Create a BankAccount class with private balance and deposit/withdraw methods.",
            "starter_code": (
                "class BankAccount {\n"
                "  private int balance;\n"
                "  BankAccount(int balance) { this.balance = balance; }\n"
                "  int getBalance() { return balance; }\n"
                "  void deposit(int amt) { if (amt > 0) balance += amt; }\n"
                "  boolean withdraw(int amt) {\n"
                "    if (amt <= 0 || amt > balance) return false;\n"
                "    balance -= amt;\n"
                "    return true;\n"
                "  }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    BankAccount a = new BankAccount(100);\n"
                "    a.deposit(50);\n"
                "    a.withdraw(30);\n"
                "    System.out.println(a.getBalance());\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Constructor overloading",
            "description": "Create a Point class with two constructors and print distance from origin.",
            "starter_code": (
                "class Point {\n"
                "  int x;\n"
                "  int y;\n"
                "  Point() { this(0, 0); }\n"
                "  Point(int x, int y) { this.x = x; this.y = y; }\n"
                "  double dist() { return Math.sqrt(x * x + y * y); }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    Point p = new Point(3, 4);\n"
                "    System.out.println(p.dist());\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Inheritance & Polymorphism": [
        {
            "task_name": "Override method",
            "description": "Create base class Shape and override area() in Circle and Rectangle.",
            "starter_code": (
                "abstract class Shape { abstract double area(); }\n"
                "class Circle extends Shape {\n"
                "  double r;\n"
                "  Circle(double r) { this.r = r; }\n"
                "  double area() { return Math.PI * r * r; }\n"
                "}\n"
                "class Rectangle extends Shape {\n"
                "  double w, h;\n"
                "  Rectangle(double w, double h) { this.w = w; this.h = h; }\n"
                "  double area() { return w * h; }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    Shape[] shapes = { new Circle(2), new Rectangle(3, 4) };\n"
                "    for (Shape s : shapes) System.out.println(s.area());\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Polymorphic printing",
            "description": "Create Animal class and override sound() for Dog and Cat; call via base reference.",
            "starter_code": (
                "class Animal { String sound() { return \"...\"; } }\n"
                "class Dog extends Animal { String sound() { return \"Bark\"; } }\n"
                "class Cat extends Animal { String sound() { return \"Meow\"; } }\n"
                "public class Main {\n"
                "  static void speak(Animal a) { System.out.println(a.sound()); }\n"
                "  public static void main(String[] args) {\n"
                "    speak(new Dog());\n"
                "    speak(new Cat());\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Use super and constructors",
            "description": "Use super() in subclass constructor and print a combined message.",
            "starter_code": (
                "class Person {\n"
                "  String name;\n"
                "  Person(String name) { this.name = name; }\n"
                "}\n"
                "class Employee extends Person {\n"
                "  int id;\n"
                "  Employee(String name, int id) { super(name); this.id = id; }\n"
                "  String info() { return name + \" (\" + id + \")\"; }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    Employee e = new Employee(\"Ravi\", 101);\n"
                "    System.out.println(e.info());\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Interfaces & Abstract Classes": [
        {
            "task_name": "Interface implementation",
            "description": "Create Printable interface and implement it in Report class.",
            "starter_code": (
                "interface Printable { void print(); }\n"
                "class Report implements Printable {\n"
                "  public void print() { System.out.println(\"Report printed\"); }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    Printable p = new Report();\n"
                "    p.print();\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Abstract class template",
            "description": "Create abstract class Payment with abstract pay(); implement CardPayment.",
            "starter_code": (
                "abstract class Payment { abstract void pay(int amount); }\n"
                "class CardPayment extends Payment {\n"
                "  void pay(int amount) { System.out.println(\"Paid \" + amount + \" by card\"); }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    Payment p = new CardPayment();\n"
                "    p.pay(500);\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Default method in interface",
            "description": "Use a default method in interface and call it.",
            "starter_code": (
                "interface Logger {\n"
                "  default void info(String msg) { System.out.println(\"INFO: \" + msg); }\n"
                "}\n"
                "class App implements Logger {}\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    new App().info(\"Hello\");\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Collections Framework": [
        {
            "task_name": "ArrayList sort",
            "description": "Sort a list of integers and print the sorted list.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    List<Integer> a = new ArrayList<>(Arrays.asList(5, 2, 9, 1));\n"
                "    Collections.sort(a);\n"
                "    System.out.println(a);\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "HashMap frequency count",
            "description": "Count word frequency using HashMap and print counts.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    String[] words = {\"java\", \"java\", \"oop\", \"map\"};\n"
                "    Map<String, Integer> freq = new HashMap<>();\n"
                "    for (String w : words) freq.put(w, freq.getOrDefault(w, 0) + 1);\n"
                "    System.out.println(freq);\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "HashSet duplicates",
            "description": "Use HashSet to find duplicates in an array.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    int[] a = {1, 2, 3, 2, 4, 1};\n"
                "    Set<Integer> seen = new HashSet<>();\n"
                "    Set<Integer> dup = new HashSet<>();\n"
                "    for (int v : a) { if (!seen.add(v)) dup.add(v); }\n"
                "    System.out.println(dup);\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Streams & Lambdas": [
        {
            "task_name": "Filter and map stream",
            "description": "Filter even numbers and square them using streams.",
            "starter_code": (
                "import java.util.*;\n"
                "import java.util.stream.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    List<Integer> a = Arrays.asList(1,2,3,4,5,6);\n"
                "    List<Integer> out = a.stream().filter(x -> x % 2 == 0).map(x -> x * x).collect(Collectors.toList());\n"
                "    System.out.println(out);\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Reduce sum",
            "description": "Use stream reduce to compute sum of list elements.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    List<Integer> a = Arrays.asList(3, 7, 2, 8);\n"
                "    int sum = a.stream().reduce(0, (acc, x) -> acc + x);\n"
                "    System.out.println(sum);\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Sort strings by length",
            "description": "Sort strings using a lambda comparator and print result.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    List<String> a = new ArrayList<>(Arrays.asList(\"java\", \"stream\", \"api\", \"lambda\"));\n"
                "    a.sort((s1, s2) -> Integer.compare(s1.length(), s2.length()));\n"
                "    System.out.println(a);\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Multithreading (Basics)": [
        {
            "task_name": "Create a thread",
            "description": "Create a thread that prints numbers 1..5 with small delays.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) throws Exception {\n"
                "    Thread t = new Thread(() -> {\n"
                "      for (int i = 1; i <= 5; i++) {\n"
                "        System.out.println(\"T:\" + i);\n"
                "        try { Thread.sleep(50); } catch (InterruptedException ignored) {}\n"
                "      }\n"
                "    });\n"
                "    t.start();\n"
                "    for (int i = 1; i <= 5; i++) {\n"
                "      System.out.println(\"M:\" + i);\n"
                "      Thread.sleep(50);\n"
                "    }\n"
                "    t.join();\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Runnable vs Thread",
            "description": "Create a Runnable and run it using Thread.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) throws Exception {\n"
                "    Runnable r = () -> System.out.println(\"Runnable executed\");\n"
                "    Thread t = new Thread(r);\n"
                "    t.start();\n"
                "    t.join();\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Synchronized counter",
            "description": "Increment shared counter from two threads safely using synchronized.",
            "starter_code": (
                "class Counter {\n"
                "  private int value = 0;\n"
                "  synchronized void inc() { value++; }\n"
                "  int get() { return value; }\n"
                "}\n"
                "public class Main {\n"
                "  public static void main(String[] args) throws Exception {\n"
                "    Counter c = new Counter();\n"
                "    Thread a = new Thread(() -> { for (int i=0;i<1000;i++) c.inc(); });\n"
                "    Thread b = new Thread(() -> { for (int i=0;i<1000;i++) c.inc(); });\n"
                "    a.start(); b.start();\n"
                "    a.join(); b.join();\n"
                "    System.out.println(c.get());\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "File I/O (Read/Write)": [
        {
            "task_name": "Read all lines",
            "description": "Read input.txt line by line and print each line. (Runner provides sample input.txt.)",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try (BufferedReader br = new BufferedReader(new FileReader(\"input.txt\"))) {\n"
                "      String line;\n"
                "      while ((line = br.readLine()) != null) System.out.println(line);\n"
                "    } catch (IOException e) {\n"
                "      System.out.println(\"IO error: \" + e.getMessage());\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Write report file",
            "description": "Write a short report into out.txt and then print a success message.",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try (BufferedWriter bw = new BufferedWriter(new FileWriter(\"out.txt\"))) {\n"
                "      bw.write(\"Practice report\\n\");\n"
                "      bw.write(\"Done\\n\");\n"
                "      System.out.println(\"Written out.txt\");\n"
                "    } catch (IOException e) {\n"
                "      System.out.println(\"Write failed: \" + e.getMessage());\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Copy file",
            "description": "Copy input.txt to copy.txt using streams and handle exceptions.",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try (InputStream in = new FileInputStream(\"input.txt\");\n"
                "         OutputStream out = new FileOutputStream(\"copy.txt\")) {\n"
                "      byte[] buf = new byte[256];\n"
                "      int n;\n"
                "      while ((n = in.read(buf)) > 0) out.write(buf, 0, n);\n"
                "      System.out.println(\"Copied to copy.txt\");\n"
                "    } catch (IOException e) {\n"
                "      System.out.println(\"Copy failed: \" + e.getMessage());\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "DSA: Searching & Sorting": [
        {
            "task_name": "Binary search",
            "description": "Implement binary search on sorted array and print index of target.",
            "starter_code": (
                "public class Main {\n"
                "  static int bs(int[] a, int t) {\n"
                "    int lo = 0, hi = a.length - 1;\n"
                "    while (lo <= hi) {\n"
                "      int mid = lo + (hi - lo) / 2;\n"
                "      if (a[mid] == t) return mid;\n"
                "      if (a[mid] < t) lo = mid + 1; else hi = mid - 1;\n"
                "    }\n"
                "    return -1;\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    int[] a = {1,3,4,6,8,9,12};\n"
                "    System.out.println(bs(a, 8));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Bubble sort",
            "description": "Sort an array using bubble sort and print the result.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  static void bubble(int[] a) {\n"
                "    for (int i = 0; i < a.length; i++) {\n"
                "      for (int j = 0; j + 1 < a.length - i; j++) {\n"
                "        if (a[j] > a[j+1]) { int t = a[j]; a[j]=a[j+1]; a[j+1]=t; }\n"
                "      }\n"
                "    }\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    int[] a = {5, 1, 4, 2, 8};\n"
                "    bubble(a);\n"
                "    System.out.println(Arrays.toString(a));\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Two sum",
            "description": "Find two indices such that a[i]+a[j]=target and print them.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  static int[] twoSum(int[] a, int target) {\n"
                "    Map<Integer, Integer> m = new HashMap<>();\n"
                "    for (int i = 0; i < a.length; i++) {\n"
                "      int need = target - a[i];\n"
                "      if (m.containsKey(need)) return new int[] { m.get(need), i };\n"
                "      m.put(a[i], i);\n"
                "    }\n"
                "    return new int[] {-1, -1};\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    int[] a = {2,7,11,15};\n"
                "    int[] ans = twoSum(a, 9);\n"
                "    System.out.println(ans[0] + \",\" + ans[1]);\n"
                "  }\n"
                "}\n"
            ),
        },
    ],
    "File Handling Exceptions": [
        {
            "task_name": "Read file with try-catch",
            "description": "Read a text file and handle FileNotFoundException gracefully.",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try {\n"
                "      BufferedReader br = new BufferedReader(new FileReader(\"input.txt\"));\n"
                "      System.out.println(br.readLine());\n"
                "      br.close();\n"
                "    } catch (FileNotFoundException e) {\n"
                "      System.out.println(\"File missing: \" + e.getMessage());\n"
                "    } catch (IOException e) {\n"
                "      System.out.println(\"IO error: \" + e.getMessage());\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Write file safely",
            "description": "Write text to file and handle IOException with proper cleanup.",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    BufferedWriter bw = null;\n"
                "    try {\n"
                "      bw = new BufferedWriter(new FileWriter(\"out.txt\"));\n"
                "      bw.write(\"Hello\");\n"
                "    } catch (IOException e) {\n"
                "      System.out.println(\"Write failed: \" + e.getMessage());\n"
                "    } finally {\n"
                "      try { if (bw != null) bw.close(); } catch (IOException ignored) {}\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Parse file numbers",
            "description": "Read a file line and handle NumberFormatException while parsing integer.",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try {\n"
                "      String text = \"abc\";\n"
                "      int n = Integer.parseInt(text);\n"
                "      System.out.println(n);\n"
                "    } catch (NumberFormatException e) {\n"
                "      System.out.println(\"Invalid number: \" + e.getMessage());\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Collections and Null Safety": [
        {
            "task_name": "Null list handling",
            "description": "Handle NullPointerException while reading from a null list reference.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    List<String> names = null;\n"
                "    try {\n"
                "      System.out.println(names.get(0));\n"
                "    } catch (NullPointerException e) {\n"
                "      System.out.println(\"Null list handled\");\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Index bounds handling",
            "description": "Catch IndexOutOfBoundsException when list index is invalid.",
            "starter_code": (
                "import java.util.*;\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    List<Integer> nums = Arrays.asList(1, 2, 3);\n"
                "    try {\n"
                "      System.out.println(nums.get(10));\n"
                "    } catch (IndexOutOfBoundsException e) {\n"
                "      System.out.println(\"Invalid index\");\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Multiple catch with collections",
            "description": "Use multiple catch blocks for NumberFormatException and NullPointerException.",
            "starter_code": (
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    String value = null;\n"
                "    try {\n"
                "      int n = Integer.parseInt(value);\n"
                "      System.out.println(n);\n"
                "    } catch (NumberFormatException e) {\n"
                "      System.out.println(\"Number error\");\n"
                "    } catch (NullPointerException e) {\n"
                "      System.out.println(\"Null value\");\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
    ],
    "Custom Exceptions": [
        {
            "task_name": "Throw custom exception",
            "description": "Create and throw a custom exception for invalid age input.",
            "starter_code": (
                "class InvalidAgeException extends Exception {\n"
                "  InvalidAgeException(String msg) { super(msg); }\n"
                "}\n"
                "public class Main {\n"
                "  static void validate(int age) throws InvalidAgeException {\n"
                "    if (age < 18) throw new InvalidAgeException(\"Age must be 18+\");\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    try { validate(15); } catch (InvalidAgeException e) { System.out.println(e.getMessage()); }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "Rethrow checked exception",
            "description": "Catch IOException and rethrow it with additional context.",
            "starter_code": (
                "import java.io.*;\n"
                "public class Main {\n"
                "  static void load() throws IOException {\n"
                "    try { throw new IOException(\"Disk read failed\"); }\n"
                "    catch (IOException e) { throw new IOException(\"Load failed: \" + e.getMessage()); }\n"
                "  }\n"
                "  public static void main(String[] args) {\n"
                "    try { load(); } catch (IOException e) { System.out.println(e.getMessage()); }\n"
                "  }\n"
                "}"
            ),
        },
        {
            "task_name": "finally with custom flow",
            "description": "Use finally to ensure cleanup after custom exception path.",
            "starter_code": (
                "class AppException extends Exception { AppException(String m) { super(m); } }\n"
                "public class Main {\n"
                "  public static void main(String[] args) {\n"
                "    try {\n"
                "      throw new AppException(\"App flow broke\");\n"
                "    } catch (AppException e) {\n"
                "      System.out.println(e.getMessage());\n"
                "    } finally {\n"
                "      System.out.println(\"Cleanup done\");\n"
                "    }\n"
                "  }\n"
                "}"
            ),
        },
    ],
}


def _normalize_topic(topic: str) -> str:
    return " ".join((topic or "").strip().lower().split())


def _topic_tasks_from_bank(topic: str, count: int) -> list[dict] | None:
    query = _normalize_topic(topic)
    if not query:
        return None
    for bank_topic, tasks in TOPIC_TASK_BANK.items():
        bank_norm = _normalize_topic(bank_topic)
        if query in bank_norm or bank_norm in query:
            return tasks[:count]
    keyword_map = {
        "basic": "Java Basics (Variables & Operators)",
        "variable": "Java Basics (Variables & Operators)",
        "operator": "Java Basics (Variables & Operators)",
        "loop": "Control Flow (if/switch/loops)",
        "switch": "Control Flow (if/switch/loops)",
        "if": "Control Flow (if/switch/loops)",
        "array": "Arrays & Strings",
        "string": "Arrays & Strings",
        "recursion": "Methods & Recursion",
        "method": "Methods & Recursion",
        "oop": "OOP: Classes & Objects",
        "class": "OOP: Classes & Objects",
        "object": "OOP: Classes & Objects",
        "inherit": "Inheritance & Polymorphism",
        "polymorphism": "Inheritance & Polymorphism",
        "interface": "Interfaces & Abstract Classes",
        "abstract": "Interfaces & Abstract Classes",
        "stream": "Streams & Lambdas",
        "lambda": "Streams & Lambdas",
        "thread": "Multithreading (Basics)",
        "sync": "Multithreading (Basics)",
        "sort": "DSA: Searching & Sorting",
        "search": "DSA: Searching & Sorting",
        "dsa": "DSA: Searching & Sorting",
        "file": "File Handling Exceptions",
        "io": "File Handling Exceptions",
        "null": "Collections and Null Safety",
        "collection": "Collections and Null Safety",
        "custom": "Custom Exceptions",
        "user-defined": "Custom Exceptions",
        "exception": "Java Exception Basics",
    }
    for keyword, mapped_topic in keyword_map.items():
        if keyword in query:
            return TOPIC_TASK_BANK[mapped_topic][:count]
    return None


def get_topic_catalog() -> list[dict]:
    catalog: list[dict] = []
    for topic, tasks in TOPIC_TASK_BANK.items():
        catalog.append(
            {
                "topic": topic,
                "tasks": [
                    {"task_name": task["task_name"], "description": task["description"]}
                    for task in tasks
                ],
            }
        )
    return catalog


def _validate_tasks(items: list[dict], language: str) -> list[dict]:
    valid = []
    name_counts: dict[str, int] = {}
    language_key = _normalize_language(language)
    for item in items:
        task_name = str(item.get("task_name", "")).strip()
        description = str(item.get("description", "")).strip()
        starter_code = str(item.get("starter_code", "")).strip()
        if not task_name or not description or not starter_code:
            continue
        code_lower = starter_code.lower()
        if language_key == "java":
            if "class" not in code_lower or "main" not in code_lower:
                continue
        elif language_key in {"c", "c++"}:
            if "int main" not in code_lower:
                continue
        elif language_key == "javascript":
            if "function" not in code_lower and "=>" not in starter_code and "console.log" not in code_lower:
                continue
        else:
            if "def " not in code_lower and "if __name__" not in code_lower:
                continue
        key = task_name.lower()
        idx = name_counts.get(key, 0) + 1
        name_counts[key] = idx
        unique_name = task_name if idx == 1 else f"{task_name} ({idx})"
        valid.append(
            {
                "task_name": unique_name,
                "description": description,
                "starter_code": starter_code,
            }
        )
    return valid


def _generate_ai_practice_tasks(topic: str, language: str, count: int) -> tuple[list[dict], str]:
    language_key = _normalize_language(language)
    language_label = _language_display(language_key)
    system_prompt = (
        "You create practical coding exercises for learners. Return strict JSON only with key tasks. "
        "Each task must contain task_name, description, starter_code. "
        "The starter_code should be a runnable starting scaffold with TODO comments and no full solution. "
        "Keep the tasks short, useful, and language-specific. No markdown."
    )
    user_prompt = (
        f"Language: {language_label}\n"
        f"Topic: {(topic or 'the current concept').strip()}\n"
        f"Number of tasks: {count}\n\n"
        "Return JSON object:\n"
        "{\n"
        "  \"tasks\": [\n"
        "    {\n"
        "      \"task_name\": \"...\",\n"
        "      \"description\": \"...\",\n"
        "      \"starter_code\": \"...\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        f"- Every task must be written for {language_label}\n"
        "- Make each description ask the learner to complete the logic themselves\n"
        "- starter_code must include a clear TODO and an input/output scaffold\n"
        "- Avoid full solutions\n"
    )
    payload = chatgpt_json(system_prompt, user_prompt, temperature=0.45)
    if not payload or not isinstance(payload.get("tasks"), list):
        return [], "unavailable"
    tasks = _validate_tasks(payload["tasks"], language_key)
    return tasks[: max(1, min(5, count))], "ai"


def _is_low_signal_topic(topic: str) -> bool:
    text = (topic or "").strip().lower()
    if not text:
        return True
    low_signal_phrases = {
        "i want learn new things",
        "learn new things",
        "new things",
        "hello",
        "hi",
        "help me",
        "anything",
    }
    if text in low_signal_phrases:
        return True
    return len(text.split()) < 3


def _merge_with_defaults(tasks: list[dict], count: int) -> list[dict]:
    merged: list[dict] = []
    seen = set()
    for item in tasks + DEFAULT_TASKS:
        key = item["task_name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= count:
            break
    return merged


def generate_practice_tasks_from_topic(
    topic: str,
    language: str | None = None,
    count: int = 3,
    allow_ai: bool = True,
) -> tuple[list[dict], str]:
    clean_topic = (topic or "").strip()
    language_key = _normalize_language(language)
    safe_count = max(1, min(5, int(count)))

    if allow_ai:
        tasks, source = _generate_ai_practice_tasks(clean_topic or "the current concept", language_key, safe_count)
        if tasks:
            return tasks, source

    if _allow_practice_fallback():
        bank_tasks = _topic_tasks_from_bank(clean_topic, safe_count)
        if bank_tasks:
            return bank_tasks, "catalog"
        return DEFAULT_TASKS[:safe_count], "default"

    return [], "unavailable"
