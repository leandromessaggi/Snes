#pragma once
#include <array>
#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace desert {
template<size_t Capacity> class AudioRing {
    static_assert(Capacity >= 4 && (Capacity % 2) == 0, "Need even stereo capacity");
    std::array<int16_t, Capacity> data_{};
    size_t read_ = 0, write_ = 0, used_ = 0;
public:
    void clear() { read_ = write_ = used_ = 0; }
    size_t pending() const { return used_; }
    void push(int16_t left, int16_t right) {
        if (used_ == Capacity) { read_ = (read_ + 2) % Capacity; used_ -= 2; }
        data_[write_] = left; data_[(write_ + 1) % Capacity] = right;
        write_ = (write_ + 2) % Capacity; used_ += 2;
    }
    size_t drain(int16_t* out, size_t requested) {
        if (!out) return 0;
        const size_t count = (std::min(used_, requested) / 2) * 2;
        for (size_t i = 0; i < count; ++i) { out[i] = data_[read_]; read_ = (read_ + 1) % Capacity; }
        used_ -= count; return count;
    }
};
}
