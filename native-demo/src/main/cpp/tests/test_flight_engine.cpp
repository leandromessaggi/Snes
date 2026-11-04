#include "../flight_engine.hpp"
#include <cassert>
#include <vector>
#include <cstdint>
#include <cstdio>
int main() {
    romnative::FlightEngine e;
    std::vector<uint8_t> rom(1024*1024);
    for(size_t i=0;i<rom.size();++i) rom[i]=uint8_t(i);
    assert(!e.load(nullptr,0));
    assert(e.load(rom.data(),rom.size()));
    const float x=e.x(),y=e.y();
    e.step(romnative::RIGHT|romnative::UP|romnative::FIRE,0.03f);
    assert(e.x()>x && e.y()<y && e.frames()==1 && e.shotCount()==1);
    std::vector<uint32_t> frame(romnative::WIDTH*romnative::HEIGHT);
    e.render(frame.data(),frame.size());
    assert(frame[0]!=0 && frame[romnative::WIDTH*120+160]!=0);
    // Transparent edges do not replace the terrain; opaque pixels do.
    const uint32_t picture[9]={0,0,0,0,0xffff3311u,0,0,0,0};
    assert(!e.setHelicopterSprite(picture,8,3,3));
    assert(e.setHelicopterSprite(picture,9,3,3));
    assert(e.hasHelicopterSprite());
    e.render(frame.data(),frame.size());
    const int centerX=int(e.x()), centerY=int(e.y());
    assert(frame[centerY*romnative::WIDTH+centerX]==0xffff3311u);
    uint32_t blank[9]{};
    assert(!e.setHelicopterSprite(blank,9,3,3));
    assert(e.hasHelicopterSprite());
    // A semi-transparent pixel must blend instead of writing its RGB verbatim.
    uint32_t semi[]={0x8000ff00u};
    assert(e.setHelicopterSprite(semi,1,1,1));
    e.render(frame.data(),frame.size());
    const auto blended=frame[centerY*romnative::WIDTH+centerX];
    assert((blended & 0xff000000u)==0xff000000u);
    assert((blended & 0x0000ff00u)!=0);
    assert(blended!=semi[0]);

    for(int i=0;i<200;++i)e.step(romnative::LEFT|romnative::DOWN,0.04f);
    assert(e.x()>=20 && e.y()<=romnative::HEIGHT-25);
    e.reset();
    assert(e.frames()==0 && e.shotCount()==0);
    assert(e.heading()==0);
    // Atlas of eight uniquely colored 3x3 frames, one direction per cell.
    uint32_t atlas[3*8*3]{};
    for(int y=0;y<3;++y)for(int direction=0;direction<8;++direction)
        atlas[y*24+direction*3+1]=0xff000010u+static_cast<uint32_t>(direction);
    assert(!e.setHelicopterAtlas(atlas,72,24,3,7));
    assert(e.setHelicopterAtlas(atlas,72,24,3,8));
    assert(e.spriteFrames()==8);
    const uint32_t cmds[8]={romnative::UP,romnative::UP|romnative::RIGHT,
        romnative::RIGHT,romnative::RIGHT|romnative::DOWN,romnative::DOWN,
        romnative::DOWN|romnative::LEFT,romnative::LEFT,romnative::LEFT|romnative::UP};
    for(int i=0;i<8;++i){
        e.step(cmds[i],0.016f);
        assert(e.heading()==i);
        e.render(frame.data(),frame.size());
        assert(frame[int(e.y())*romnative::WIDTH+int(e.x())]==
            0xff000010u+static_cast<uint32_t>(i));
    }
    e.step(0,0.016f);
    assert(e.heading()==7);
    // The original v1 single-image API still works after an eight-frame pack.
    assert(e.setHelicopterSprite(picture,9,3,3));
    assert(e.spriteFrames()==1);

    std::puts("PASS native flight engine (no emulator dependency)");
}
