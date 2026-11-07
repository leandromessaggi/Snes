#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <vector>

namespace romnative {
// Original mission prototype. Mission files are data, not original SNES scripts.
class CombatMission {
public:
    static constexpr int TARGET_COUNT=4; // original fallback for existing tests
    static constexpr int MAX_TARGETS=12;
    enum class State : int { Playing=0, Won=1, Lost=2 };
    enum class Type : int { Depot=0, Turret=1, Patrol=2 };
    struct TargetSpec {
        float x,y;
        int hp;
        int type;
        int patrolRange;
    };
    struct Target {
        float x,y;
        int hp,maxHp;
        float cooldown;
        bool turret;
        int type;
        float homeX, direction, patrolRange;
    };
    struct HostileShot {float x,y,vx,vy;};
    struct Blast {float x,y,ttl;};

    CombatMission(){useDefaults();}
    static bool validSpecs(const std::vector<TargetSpec>& list) {
        if(list.empty() || list.size()>MAX_TARGETS)return false;
        for(size_t i=0;i<list.size();++i){
            const auto& t=list[i];
            if(!std::isfinite(t.x) || !std::isfinite(t.y) ||
               t.x<22 || t.x>298 || t.y<34 || t.y>218 ||
               t.hp<1 || t.hp>9 || t.type<0 || t.type>2 ||
               t.patrolRange<0 || t.patrolRange>32 ||
               (t.type!=2 && t.patrolRange!=0) ||
               (t.type==2 && t.patrolRange<8) ||
               t.x-t.patrolRange<18 || t.x+t.patrolRange>302)
                return false;
            for(size_t j=0;j<i;++j){
                const float dx=t.x-list[j].x,dy=t.y-list[j].y;
                if(dx*dx+dy*dy < 26.f*26.f) return false;
            }
        }
        return true;
    }
    bool configure(const std::vector<TargetSpec>& list) {
        if(!validSpecs(list))return false; // reject atomically
        blueprint_=list;
        reset();
        return true;
    }
    void useDefaults() {
        blueprint_={
            {78.f,73.f,2,1,0},
            {263.f,166.f,2,1,0},
            {250.f,132.f,2,0,0},
            {104.f,195.f,3,0,0}
        };
        reset();
    }
    void reset() {
        targets_.clear();
        for(const auto& s:blueprint_) {
            targets_.push_back({
                s.x,s.y,s.hp,s.hp,.5f+float(targets_.size()),s.type!=0,
                s.type,s.x,1.f,float(s.patrolRange)
            });
        }
        bullets_.clear();blasts_.clear();
        health_=100;invulnerable_=0.f;destroyed_=0;state_=State::Playing;
    }
    int health()const{return health_;}
    int destroyed()const{return destroyed_;}
    int total()const{return static_cast<int>(targets_.size());}
    int remaining()const{return total()-destroyed_;}
    State state()const{return state_;}
    float invulnerableTime()const{return invulnerable_;}
    const std::vector<Target>& targets()const{return targets_;}
    const std::vector<HostileShot>& hostileShots()const{return bullets_;}
    const std::vector<Blast>& blasts()const{return blasts_;}
    bool hit(float x,float y){
        if(state_!=State::Playing)return false;
        for(auto& t:targets_){
            if(t.hp<=0)continue;
            const float dx=x-t.x,dy=y-t.y;
            if(dx*dx+dy*dy>14.f*14.f)continue;
            --t.hp;
            if(t.hp==0){
                ++destroyed_;
                addBlast(t.x,t.y,.7f);
                if(destroyed_==total())state_=State::Won;
            } else addBlast(x,y,.2f);
            return true;
        }
        return false;
    }
    void update(float dt,float heliX,float heliY){
        if(!std::isfinite(dt) || dt<=0.f)return;
        dt=std::min(dt,.05f);
        for(auto& b:blasts_)b.ttl-=dt;
        blasts_.erase(std::remove_if(blasts_.begin(),blasts_.end(),
            [](const Blast& b){return b.ttl<=0.f;}),blasts_.end());
        invulnerable_=std::max(0.f,invulnerable_-dt);
        if(state_!=State::Playing)return;

        for(auto& t:targets_){
            if(t.hp<=0)continue;
            if(t.type==2) {
                t.x+=t.direction*26.f*dt;
                if(t.x>t.homeX+t.patrolRange){
                    t.x=t.homeX+t.patrolRange;t.direction=-1.f;
                } else if(t.x<t.homeX-t.patrolRange){
                    t.x=t.homeX-t.patrolRange;t.direction=1.f;
                }
            }
            if(!t.turret)continue;
            t.cooldown-=dt;
            if(t.cooldown>0.f)continue;
            const float dx=heliX-t.x,dy=heliY-t.y;
            const float len=std::sqrt(dx*dx+dy*dy);
            if(len>5.f && len<185.f && bullets_.size()<48){
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
                if(dx*dx+dy*dy<=11.f*11.f){
                    damage(12,heliX,heliY);return true;
                }
                return false;
            }),bullets_.end());
        if(invulnerable_<=0.f){
            for(const auto& t:targets_){
                if(t.hp<=0)continue;
                const float dx=heliX-t.x,dy=heliY-t.y;
                if(dx*dx+dy*dy<20.f*20.f){
                    damage(10,heliX,heliY);break;
                }
            }
        }
    }
private:
    void damage(int amount,float x,float y){
        if(invulnerable_>0.f || state_!=State::Playing)return;
        health_=std::max(0,health_-amount);
        invulnerable_=.75f;
        addBlast(x,y,.25f);
        if(health_==0)state_=State::Lost;
    }
    void addBlast(float x,float y,float ttl){
        if(blasts_.size()<24)blasts_.push_back({x,y,ttl});
    }
    std::vector<TargetSpec> blueprint_;
    std::vector<Target> targets_;
    std::vector<HostileShot> bullets_;
    std::vector<Blast> blasts_;
    int health_=100,destroyed_=0;
    float invulnerable_=0.f;
    State state_=State::Playing;
};
} // namespace romnative
