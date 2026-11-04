#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>
namespace romnative {
/** ARGB8888 premultiplied-independent atlas; frames arranged horizontally.
 * For an animated helicopter the sprite sheet has precisely eight directions
 * N, NE, E, SE, S, SW, W, NW; legacy v1 sprites have one frame.
 */
class SpriteImage {
public:
    bool set(const uint32_t* argb,size_t count,int width,int height,int frames=1) {
        if(!argb || (frames!=1 && frames!=8) || width<1 || height<1 ||
           height>128 || width>128*frames || width%frames!=0 ||
           count!=static_cast<size_t>(width)*static_cast<size_t>(height))
           return false;
        const int frameWidth=width/frames;
        if(frameWidth<1 || frameWidth>128)return false;
        // Reject an empty frame: otherwise it looks like the helicopter disappears
        // when changing direction.
        for(int index=0;index<frames;++index) {
            bool visible=false;
            for(int y=0;y<height && !visible;++y) {
                for(int x=0;x<frameWidth;++x) {
                    if((argb[static_cast<size_t>(y)*width+index*frameWidth+x]>>24)!=0) {
                        visible=true;break;
                    }
                }
            }
            if(!visible)return false;
        }
        pixels_.assign(argb,argb+count);
        atlasWidth_=width;frameWidth_=frameWidth;height_=height;frames_=frames;
        return true;
    }
    void clear(){pixels_.clear();atlasWidth_=frameWidth_=height_=0;frames_=0;}
    bool valid()const{return !pixels_.empty();}
    int frameCount()const{return frames_;}
    void draw(uint32_t* dst,int sw,int sh,int cx,int cy,int direction=0)const{
        if(!dst || sw<=0 || sh<=0 || !valid())return;
        const int selected=frames_==1?0:std::clamp(direction,0,frames_-1);
        const int left=cx-frameWidth_/2,top=cy-height_/2;
        for(int y=0;y<height_;++y){
            const int dy=top+y;
            if(dy<0 || dy>=sh)continue;
            for(int x=0;x<frameWidth_;++x){
                const int dx=left+x;
                if(dx<0 || dx>=sw)continue;
                const uint32_t fg=pixels_[static_cast<size_t>(y)*atlasWidth_+selected*frameWidth_+x];
                const uint32_t a=fg>>24;
                if(!a)continue;
                uint32_t& bg=dst[static_cast<size_t>(dy)*sw+dx];
                if(a==255){bg=fg;continue;}
                const auto mix=[&](unsigned shift)->uint32_t{
                    const unsigned c1=(fg>>shift)&255u,c0=(bg>>shift)&255u;
                    return (c1*a+c0*(255u-a)+127u)/255u;
                };
                bg=0xff000000u|(mix(16)<<16)|(mix(8)<<8)|mix(0);
            }
        }
    }
private:
    int atlasWidth_=0,frameWidth_=0,height_=0,frames_=0;
    std::vector<uint32_t> pixels_;
};
} // namespace romnative
