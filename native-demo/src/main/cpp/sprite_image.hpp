#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace romnative {
/** Bounded ARGB8888 sprite. Supplied pixels are unpremultiplied, as from Android Bitmap.getPixels. */
class SpriteImage {
public:
    bool set(const uint32_t* argb, size_t count, int width, int height) {
        if (!argb || width < 1 || height < 1 || width > 128 || height > 128
                || count < static_cast<size_t>(width) * height) return false;
        const size_t n = static_cast<size_t>(width) * height;
        if (std::none_of(argb, argb + n, [](uint32_t c){ return (c >> 24) != 0; }))
            return false; // An invisible sprite should not hide the placeholder.
        pixels_.assign(argb, argb + n);
        width_ = width;
        height_ = height;
        return true;
    }
    void clear() { pixels_.clear(); width_ = height_ = 0; }
    bool valid() const { return !pixels_.empty(); }
    void draw(uint32_t* frame, int screenWidth, int screenHeight,
              int centerX, int centerY) const {
        if (!frame || screenWidth <= 0 || screenHeight <= 0 || !valid()) return;
        const int left = centerX - width_ / 2;
        const int top = centerY - height_ / 2;
        for (int y = 0; y < height_; ++y) {
            const int dstY = top + y;
            if (dstY < 0 || dstY >= screenHeight) continue;
            for (int x = 0; x < width_; ++x) {
                const int dstX = left + x;
                if (dstX < 0 || dstX >= screenWidth) continue;
                const uint32_t fg = pixels_[static_cast<size_t>(y)*width_+x];
                const uint32_t alpha = fg >> 24;
                if (alpha == 0) continue;
                uint32_t& bg = frame[static_cast<size_t>(dstY)*screenWidth+dstX];
                if (alpha == 255) { bg=fg; continue; }
                const auto mix=[&](unsigned shift) -> uint32_t {
                    const unsigned c1=(fg >> shift) & 255u;
                    const unsigned c0=(bg >> shift) & 255u;
                    return (c1*alpha+c0*(255u-alpha)+127u)/255u;
                };
                bg=0xff000000u | (mix(16)<<16) | (mix(8)<<8) | mix(0);
            }
        }
    }
private:
    int width_ = 0, height_ = 0;
    std::vector<uint32_t> pixels_;
};
} // namespace romnative
