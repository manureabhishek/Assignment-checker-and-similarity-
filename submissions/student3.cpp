#include <iostream>
using namespace std;

int findMaximum(int values[]) {
    int largest = values[0];

    for (int i = 1; i < 2; i++) {
        if (values[i] > largest) {
            largest = values[i];
        }
    }

    return largest;
}

int main() {
    int numbers[2];
    cin >> numbers[0] >> numbers[1];

    cout << findMaximum(numbers);
    return 0;
}