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
        previous_.assign(p, p+n); allChanges_.assign(n, 0); buttonChanges_.assign(n, {}); active_ = true; return true;
    }
    bool active() const { return active_; }
    size_t count() const { return frames_.size(); }
    void capture(const void* memory, size_t n, uint16_t buttons) {
        if (!active_) return;
        if (!memory || n != previous_.size()) { active_ = false; return; }
        const auto* p = static_cast<const uint8_t*>(memory);
        Frame f{static_cast<uint32_t>(frames_.size()), buttons, 0, {}};
        for (unsigned b=0;b<12;++b) if (buttons & (1u<<b)) ++buttonFrames_[b];
        for (size_t i=0; i<n; ++i) {
            if (p[i] == previous_[i]) continue;
            ++f.changed;
            ++allChanges_[i];
            for (unsigned b=0;b<12;++b) if (buttons & (1u<<b)) ++buttonChanges_[i][b];
            if (f.preview.size() < MAX_PREVIEW)
                f.preview.push_back({static_cast<uint32_t>(i), previous_[i], p[i]});
            previous_[i] = p[i];
        }
        frames_.push_back(std::move(f));
        if (frames_.size() >= MAX_FRAMES) active_ = false;
    }
    std::string json() const {
        std::string s = "{\"schema\":\"desert-wram-diff-v2\",\"memory_bytes\":" +
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
        // Per-frame previews are capped; rankings consider ALL changed offsets.
        s += "],\"rankings\":[";
        for (unsigned b=0;b<12;++b) {
            if (b) s += ",";
            const uint32_t onFrames=buttonFrames_[b];
            const uint32_t offFrames=static_cast<uint32_t>(frames_.size())-onFrames;
            s += "{\"button\":"+std::to_string(b)+",\"frames_on\":"+std::to_string(onFrames)+
                 ",\"frames_off\":"+std::to_string(offFrames)+",\"top\":[";
            if (onFrames>=2 && offFrames>=2) {
                // Candidate: [lift numerator, RAM offset, on changes, off changes].
                std::vector<std::array<int64_t,4>> candidates;
                for (size_t i=0;i<allChanges_.size();++i) {
                    const uint32_t on=buttonChanges_[i][b], off=allChanges_[i]-on;
                    const int64_t lift=static_cast<int64_t>(on)*offFrames-
                                       static_cast<int64_t>(off)*onFrames;
                    if (lift>0) candidates.push_back({lift,static_cast<int64_t>(i),on,off});
                }
                const size_t limit=std::min(size_t(24),candidates.size());
                std::partial_sort(candidates.begin(),candidates.begin()+limit,candidates.end(),
                    [](const auto& x,const auto& y){return x[0]>y[0] || (x[0]==y[0] && x[1]<y[1]);});
                for (size_t i=0;i<limit;++i) {
                    if (i) s += ",";
                    const auto& c=candidates[i];
                    s += "["+std::to_string(c[1])+","+std::to_string(c[2])+","+
                         std::to_string(c[3])+","+std::to_string(c[0])+"]";
                }
            }
            s += "]}";
        }
        return s + "]}";
    }
    void clear() { active_ = false; previous_.clear(); frames_.clear(); allChanges_.clear(); buttonChanges_.clear(); buttonFrames_.fill(0); }
private:
    bool active_ = false;
    std::vector<uint8_t> previous_;
    std::vector<Frame> frames_;
    std::vector<uint16_t> allChanges_;
    std::vector<std::array<uint16_t,12>> buttonChanges_;
    std::array<uint32_t,12> buttonFrames_{};
};
}
