#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <vector>

namespace romnative {

// ORIGINAL gameplay prototype, not decompiled Desert Strike rules/mission data.
// A small, deterministic simulation independent of Android and SNES emulation.
class CombatMission {
public:
    static constexpr int TARGET_COUNT=4;
    enum class State : int { Playing=0, Won=1, Lost=2 };
    struct Target {
        float x,y;
        int hp,maxHp;
        float cooldown;
        bool turret;
    };
    struct HostileShot {float x,y,vx,vy;};
    struct Blast {float x,y,ttl;};
    CombatMission(){reset();}
    void reset(){
        targets_={{
            {78.f,73.f,2,2,.5f,true},
            {263.f,166.f,2,2,1.5f,true},
            {250.f,132.f,2,2,2.5f,false},
            {104.f,195.f,3,3,3.5f,false}
        }};
        bullets_.clear();blasts_.clear();
        health_=100;invulnerable_=0;destroyed_=0;state_=State::Playing;
    }
    int health()const{return health_;}
    int destroyed()const{return destroyed_;}
    int remaining()const{return TARGET_COUNT-destroyed_;}
    State state()const{return state_;}
    float invulnerableTime()const{return invulnerable_;}
    const std::array<Target,TARGET_COUNT>& targets()const{return targets_;}
    const std::vector<HostileShot>& hostileShots()const{return bullets_;}
    const std::vector<Blast>& blasts()const{return blasts_;}

    // First target hit by a friendly projectile consumes exactly that projectile.
    bool hit(float x,float y) {
        if(state_!=State::Playing)return false;
        for(auto& t:targets_){
            if(t.hp<=0)continue;
            const float dx=x-t.x,dy=y-t.y;
            if(dx*dx+dy*dy>14.f*14.f)continue;
            --t.hp;
            if(t.hp==0) {
                ++destroyed_;
                addBlast(t.x,t.y,.7f);
                if(destroyed_==TARGET_COUNT)state_=State::Won;
            } else {
                addBlast(x,y,.2f);
            }
            return true;
        }
        return false;
    }

    void update(float dt,float heliX,float heliY) {
        if(!std::isfinite(dt) || dt<=0) return;
        dt=std::min(dt,.05f);
        for(auto& b:blasts_)b.ttl-=dt;
        blasts_.erase(std::remove_if(blasts_.begin(),blasts_.end(),
            [](const Blast& b){return b.ttl<=0;}),blasts_.end());
        invulnerable_=std::max(0.f,invulnerable_-dt);
        if(state_!=State::Playing)return;

        // Turrets only acquire the player inside their line-of-sight range.
        for(auto& t:targets_){
            if(t.hp<=0 || !t.turret)continue;
            t.cooldown-=dt;
            if(t.cooldown>0)continue;
            const float dx=heliX-t.x,dy=heliY-t.y;
            const float len=std::sqrt(dx*dx+dy*dy);
            if(len>5.f && len<185.f && bullets_.size()<48) {
                const float vx=dx/len,vy=dy/len;
                bullets_.push_back({t.x+vx*13.f,t.y+vy*13.f,
                                    vx*88.f,vy*88.f});
            }
            t.cooldown=1.6f;
        }
        for(auto& bullet:bullets_){
            bullet.x+=bullet.vx*dt;
            bullet.y+=bullet.vy*dt;
        }
        bullets_.erase(std::remove_if(bullets_.begin(),bullets_.end(),
            [&](const HostileShot& bullet){
                if(bullet.x<0 || bullet.y<0 || bullet.x>=320 || bullet.y>=240)
                    return true;
                const float dx=bullet.x-heliX,dy=bullet.y-heliY;
                if(dx*dx+dy*dy <= 11.f*11.f){
                    damage(12,heliX,heliY);
                    return true;
                }
                return false;
            }),bullets_.end());
        if(invulnerable_<=0){
            for(const auto& t:targets_){
                if(t.hp<=0)continue;
                const float dx=heliX-t.x,dy=heliY-t.y;
                if(dx*dx+dy*dy<20.f*20.f) {
                    damage(10,heliX,heliY);
                    break;
                }
            }
        }
    }
private:
    void damage(int amount,float x,float y){
        if(invulnerable_>0 || state_!=State::Playing)return;
        health_=std::max(0,health_-amount);
        invulnerable_=.75f;
        addBlast(x,y,.25f);
        if(health_==0)state_=State::Lost;
    }
    void addBlast(float x,float y,float ttl){
        if(blasts_.size()<24)blasts_.push_back({x,y,ttl});
    }
    std::array<Target,TARGET_COUNT> targets_{};
    std::vector<HostileShot> bullets_;
    std::vector<Blast> blasts_;
    int health_=100,destroyed_=0;
    float invulnerable_=0;
    State state_=State::Playing;
};
} // namespace romnative
