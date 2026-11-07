#include "../combat_mission.hpp"
#include <cassert>
#include <cstdio>
#include <limits>
#include <vector>
int main(){
    romnative::CombatMission m;
    using State=romnative::CombatMission::State;
    using Spec=romnative::CombatMission::TargetSpec;
    assert(m.state()==State::Playing);
    assert(m.health()==100 && m.remaining()==4 && m.destroyed()==0);
    assert(!m.hit(0,0));
    assert(m.hit(250,132));
    assert(m.targets()[2].hp==1);
    assert(m.hit(250,132));
    assert(m.destroyed()==1 && m.remaining()==3);
    assert(!m.hit(250,132));
    m.update(.016f,78,73);
    assert(m.health()==90);
    m.update(.016f,78,73);
    assert(m.health()==90);
    for(int i=0;i<60;++i)m.update(.016f,0,220);
    assert(m.invulnerableTime()==0);
    for(int i=0;i<10;++i){
        for(int n=0;n<60;++n)m.update(.016f,78,73);
        if(m.state()==State::Lost)break;
    }
    assert(m.state()==State::Lost && m.health()==0);
    assert(!m.hit(78,73));
    m.reset();
    assert(m.health()==100 && m.destroyed()==0);
    for(const auto& t:m.targets()){
        const int hp=t.hp;
        for(int k=0;k<hp;++k)assert(m.hit(t.x,t.y));
    }
    assert(m.destroyed()==4 && m.state()==State::Won);
    m.update(.02f,140,120);
    assert(m.state()==State::Won);
    assert(!m.hit(200,200));

    // External mission configuration is validated atomically.
    std::vector<Spec> custom={{70,80,2,1,0},{220,150,3,2,24},{145,180,1,0,0}};
    assert(m.configure(custom));
    assert(m.total()==3 && m.remaining()==3 && m.health()==100);
    const auto before=m.targets()[1].x;
    for(int i=0;i<30;++i)m.update(.016f,130,30);
    assert(m.targets()[1].x>before); // patrol moves
    const auto moved=m.targets()[1].x;
    assert(m.hit(moved,m.targets()[1].y));
    assert(m.targets()[1].hp==2);
    m.reset();
    assert(m.total()==3 && m.targets()[1].x==220.f);
    assert(!m.configure({{70,80,1,1,0},{76,82,1,0,0}})); // overlapping
    assert(!m.configure({{70,80,0,0,0}})); // no HP
    assert(!m.configure({{70,80,1,2,0}})); // patrol requires range
    assert(!m.configure({{70,80,1,0,2}})); // depot cannot patrol
    assert(!m.configure({{70,80,1,2,50}})); // range limit
    assert(!m.configure({{std::numeric_limits<float>::quiet_NaN(),80,1,1,0}}));
    assert(!m.configure(std::vector<Spec>(13,{70,80,1,0,0})));
    assert(m.total()==3 && m.health()==100); // rejected config left untouched
    for(const auto& t:m.targets()){
        const int hp=t.hp;
        for(int k=0;k<hp;++k)assert(m.hit(t.x,t.y));
    }
    assert(m.state()==State::Won && m.destroyed()==3);
    m.useDefaults();
    assert(m.total()==4 && m.health()==100);
    std::puts("PASS combat engine: default + data-driven missions, patrol, hits, win/loss, config validation");
}
