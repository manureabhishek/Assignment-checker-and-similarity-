#include <iostream>
using namespace std;

int main() {
    int x, y;
    cin >> x >> y;

    int maximum = (x >= y) ? x : y;
    cout << maximum;

    return 0;
}