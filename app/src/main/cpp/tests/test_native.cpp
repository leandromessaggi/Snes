#include "../audio_ring.hpp"
#include "../ram_trace.hpp"
#include <cassert>
#include <cstdint>
#include <string>
int main() {
    desert::AudioRing<4> ring;
    ring.push(10,20);
    ring.push(30,40);
    ring.push(50,60);
    int16_t out[4]{};
    assert(ring.drain(out, 4)==4);
    assert(out[0]==30 && out[1]==40 && out[2]==50 && out[3]==60);
    uint8_t ram[128]{};
    desert::RamTrace trace;
    assert(trace.begin(ram,sizeof(ram)));
    ram[8]=3;
    trace.capture(ram,sizeof(ram),1);
    assert(trace.count()==1);
    const auto json=trace.json();
    assert(json.find("\"offset\"")==std::string::npos);
    assert(json.find("[8,0,3]")!=std::string::npos);
    trace.clear();
    assert(trace.count()==0);
}
