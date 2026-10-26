#include <iostream>
using namespace std;

int getMax(int first, int second) {
    return (first > second) ? first : second;
}

int main() {
    int val1, val2;
    cin >> val1 >> val2;
    cout << getMax(val1, val2);
    return 0;
}