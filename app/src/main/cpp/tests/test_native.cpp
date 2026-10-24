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
    // Verify an offset outside the 32-entry preview is ranked.
    uint8_t many[256]{};
    desert::RamTrace ranked;
    assert(ranked.begin(many,sizeof(many)));
    for (unsigned frame=0;frame<20;++frame) {
        for (unsigned i=0;i<48;++i) many[i]^=1;
        if (frame>=10) many[200]^=1;
        ranked.capture(many,sizeof(many),frame>=10 ? (1u<<6) : 0);
    }
    const auto ranking=ranked.json();
    assert(ranking.find("desert-wram-diff-v2")!=std::string::npos);
    assert(ranking.find("\"button\":6,\"frames_on\":10,\"frames_off\":10,\"top\":[[200,10,0,100]")!=std::string::npos);
    assert(ranking.find("[200,0,1]")==std::string::npos);
    ranked.clear();
    assert(ranked.count()==0);
    trace.clear();
    assert(trace.count()==0);
}
