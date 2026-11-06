#include "../combat_mission.hpp"
#include <cassert>
#include <cstdio>
int main(){
    romnative::CombatMission m;
    assert(m.state()==romnative::CombatMission::State::Playing);
    assert(m.health()==100 && m.remaining()==4 && m.destroyed()==0);
    assert(!m.hit(0,0));
    assert(m.hit(250,132));
    assert(m.targets()[2].hp==1);
    assert(m.hit(250,132));
    assert(m.destroyed()==1 && m.remaining()==3);
    assert(!m.hit(250,132));
    // Collisions with alive targets cause invulnerability-limited damage.
    m.update(.016f,78,73);
    assert(m.health()==90);
    m.update(.016f,78,73);
    assert(m.health()==90);
    for(int i=0;i<60;++i)m.update(.016f,0,220);
    assert(m.invulnerableTime()==0);
    // Defeat, then reset.
    for(int i=0;i<10;++i){
        for(int n=0;n<60;++n)m.update(.016f,78,73);
        if(m.state()==romnative::CombatMission::State::Lost)break;
    }
    assert(m.state()==romnative::CombatMission::State::Lost);
    assert(m.health()==0);
    assert(!m.hit(78,73));
    m.reset();
    assert(m.health()==100 && m.destroyed()==0);
    // All targets are destructible and winning freezes combat.
    for(const auto& t:m.targets()) {
        const int hp=t.hp;
        for(int k=0;k<hp;++k)assert(m.hit(t.x,t.y));
    }
    assert(m.destroyed()==4);
    assert(m.state()==romnative::CombatMission::State::Won);
    m.update(.02f,140,120);
    assert(m.state()==romnative::CombatMission::State::Won);
    assert(!m.hit(200,200));
    std::puts("PASS combat prototype: hits, damage, invulnerability, defeat, win, reset");
}
