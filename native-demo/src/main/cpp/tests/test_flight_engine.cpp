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
    for(int i=0;i<200;++i)e.step(romnative::LEFT|romnative::DOWN,0.04f);
    assert(e.x()>=20 && e.y()<=romnative::HEIGHT-25);
    e.reset();
    assert(e.frames()==0 && e.shotCount()==0);
    std::puts("PASS native flight engine (no emulator dependency)");
}
