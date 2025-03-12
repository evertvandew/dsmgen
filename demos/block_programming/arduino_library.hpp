
#include <array>


typedef int value_t;

struct OutputPort {
    value_t value;
};


struct InputPort {
    const value_t* value;
    InputPort() : value(null_ptr) {}
};


template<typename C>
struct Process: public C {
    uint8_t nr_inputs;

    void update_input(uint8_t index, const OutputPort* value) {
        if (index < nr_inputs) {
            get_input(index).value = value;
        }
    }
    array<uint8_t> update_outputs() {
        for (auto input: inputs()) {
            if (!input.value) {
                return [];
            }
        }
        auto values = inputs()
        return recalculate(values);
    }
};


class DO {
    Resource &pin;
    int mode;
public:
    InputPort input;

    std:array<

    DO(Resource &_pin, int _mode) : pin(_pin), mode(_mode), input(this) {}

    std::array<&InputPort, 1> inputs() {return {{&input}};}

    std::array<uint8_t> recalculate() {
        pin.set_output(*input.value);
        return [];
    }
};




void connect(InputPort& input, OutputPort& output) {
    output.connect(input);
}


Resource get_resource(const char* name) {
}