#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace desert {
// Experimental WRAM snapshots; offsets are RAM offsets, not native 65C816 addresses.
class RamTrace {
public:
    struct Change { uint32_t offset; uint8_t before; uint8_t after; };
    struct Frame { uint32_t number; uint16_t buttons; uint32_t changed; std::vector<Change> preview; };
    static constexpr size_t MAX_FRAMES = 600;
    static constexpr size_t MAX_PREVIEW = 32;
    static constexpr size_t MAX_MEMORY = 256 * 1024;
    bool begin(const void* memory, size_t n) {
        clear();
        if (!memory || n < 16 || n > MAX_MEMORY) return false;
        const auto* p = static_cast<const uint8_t*>(memory);
        previous_.assign(p, p+n); active_ = true; return true;
    }
    bool active() const { return active_; }
    size_t count() const { return frames_.size(); }
    void capture(const void* memory, size_t n, uint16_t buttons) {
        if (!active_) return;
        if (!memory || n != previous_.size()) { active_ = false; return; }
        const auto* p = static_cast<const uint8_t*>(memory);
        Frame f{static_cast<uint32_t>(frames_.size()), buttons, 0, {}};
        for (size_t i=0; i<n; ++i) {
            if (p[i] == previous_[i]) continue;
            ++f.changed;
            if (f.preview.size() < MAX_PREVIEW)
                f.preview.push_back({static_cast<uint32_t>(i), previous_[i], p[i]});
            previous_[i] = p[i];
        }
        frames_.push_back(std::move(f));
        if (frames_.size() >= MAX_FRAMES) active_ = false;
    }
    std::string json() const {
        std::string s = "{\"schema\":\"desert-wram-diff-v1\",\"memory_bytes\":" +
            std::to_string(previous_.size()) + ",\"frames\":[";
        for (size_t i=0; i<frames_.size(); ++i) {
            if (i) s += ",";
            const auto& f = frames_[i];
            s += "{\"n\":" + std::to_string(f.number) + ",\"pad\":" + std::to_string(f.buttons) +
                ",\"changed_total\":" + std::to_string(f.changed) + ",\"changes\":[";
            for (size_t j=0;j<f.preview.size();++j) {
                if(j) s += ",";
                const auto& x=f.preview[j];
                s += "[" + std::to_string(x.offset) + "," + std::to_string(x.before) + "," + std::to_string(x.after) + "]";
            }
            s += "]}";
        }
        return s + "]}";
    }
    void clear() { active_ = false; previous_.clear(); frames_.clear(); }
private:
    bool active_ = false;
    std::vector<uint8_t> previous_;
    std::vector<Frame> frames_;
};
}
