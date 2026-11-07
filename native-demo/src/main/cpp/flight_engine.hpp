#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>
#include "sprite_image.hpp"
#include "combat_mission.hpp"

namespace romnative {
// Independent C++ demonstration engine. It does NOT implement original game rules.
constexpr int WIDTH=320, HEIGHT=240;
constexpr uint32_t FIRE=1u<<0, UP=1u<<4, DOWN=1u<<5, LEFT=1u<<6, RIGHT=1u<<7;
struct Shot { float x,y,dx,dy; };
class FlightEngine {
public:
    bool load(const uint8_t* rom,size_t length) {
        if (!rom || length!=1024u*1024u) return false;
        // Data-derived terrain seed, NOT a decompiled map. No ROM bytes are retained.
        uint32_t hash=2166136261u;
        for (size_t i=0;i<length;++i) hash=(hash^rom[i])*16777619u;
        seed_=hash; ready_=true; sprite_.clear(); scene_.clear(); mission_.useDefaults(); reset(); return true;
    }
    void reset() {
        x_=160; y_=135; frames_=0; heading_=0; fireCooldown_=0;
        shots_.clear(); mission_.reset();
    }
    void restartMission(){if(ready_)reset();}
    const CombatMission& mission()const{return mission_;}
    bool configureMission(const std::vector<CombatMission::TargetSpec>& specs) {
        if(!ready_ || !mission_.configure(specs)) return false;
        x_=160.f;y_=135.f;frames_=0;heading_=0;fireCooldown_=0;shots_.clear();
        return true;
    }
    void useDefaultMission(){
        if(!ready_)return;
        mission_.useDefaults();
        x_=160.f;y_=135.f;frames_=0;heading_=0;fireCooldown_=0;shots_.clear();
    }
    bool ready() const {return ready_;}
    bool setHelicopterSprite(const uint32_t* pixels, size_t count, int width, int height) {
        return ready_ && sprite_.set(pixels,count,width,height,1);
    }
    bool hasHelicopterSprite() const {return sprite_.valid();}
    int spriteFrames() const {return sprite_.frameCount();}
    bool setHelicopterAtlas(const uint32_t* pixels,size_t count,int width,int height,int frames){
        return ready_ && sprite_.set(pixels,count,width,height,frames);
    }
    int heading() const {return heading_;}
    bool setSceneImage(const uint32_t* rgba,size_t count,int width,int height){
        if(!ready_ || !rgba || width!=WIDTH || height!=HEIGHT ||
           count!=static_cast<size_t>(WIDTH*HEIGHT)) return false;
        // A full-screen image must be opaque, avoiding render buffer leaks.
        if(!std::all_of(rgba,rgba+count,[](uint32_t c){return (c>>24)==255u;}))
            return false;
        scene_.assign(rgba,rgba+count);
        return true;
    }
    void clearScene(){scene_.clear();}
    bool hasScene() const {return scene_.size()==static_cast<size_t>(WIDTH*HEIGHT);}


    float x() const {return x_;}
    float y() const {return y_;}
    size_t shotCount() const {return shots_.size();}
    uint64_t frames() const {return frames_;}
    void step(uint32_t pad,float seconds) {
        if(!ready_ || !std::isfinite(seconds)) return;
        const float dt=std::clamp(seconds,0.0f,0.05f);
        if(mission_.state()!=CombatMission::State::Playing){
            mission_.update(dt,x_,y_); // fade existing explosions only
            return;
        }
        float dx=((pad&RIGHT)?1.f:0.f)-((pad&LEFT)?1.f:0.f);
        float dy=((pad&DOWN)?1.f:0.f)-((pad&UP)?1.f:0.f);
        const float length=std::sqrt(dx*dx+dy*dy);
        if(length>0) {
            // N, NE, E, SE, S, SW, W, NW in clockwise order.
            if (dy<0) heading_ = dx>0?1:(dx<0?7:0);
            else if(dy>0) heading_ = dx>0?3:(dx<0?5:4);
            else heading_ = dx>0?2:6;
            dx/=length; dy/=length;
        }
        x_=std::clamp(x_+dx*125.f*dt,20.f,WIDTH-20.f);
        y_=std::clamp(y_+dy*110.f*dt,28.f,HEIGHT-25.f);
        fireCooldown_=std::max(0.f,fireCooldown_-dt);
        constexpr float D=0.7071067811865475f;
        constexpr float headingDx[8]={0,D,1,D,0,-D,-1,-D};
        constexpr float headingDy[8]={-1,-D,0,D,1,D,0,-D};
        if((pad&FIRE) && fireCooldown_==0.f && shots_.size()<64){
            const float hx=headingDx[heading_], hy=headingDy[heading_];
            shots_.push_back({x_+hx*16.f,y_+hy*16.f,hx,hy});
            fireCooldown_=0.17f;
        }
        for(auto& shot:shots_){
            shot.x+=shot.dx*210.f*dt;
            shot.y+=shot.dy*210.f*dt;
        }
        shots_.erase(std::remove_if(shots_.begin(),shots_.end(),
            [&](const Shot& shot){
                if(shot.x<0 || shot.x>=WIDTH || shot.y<0 || shot.y>=HEIGHT)return true;
                return mission_.hit(shot.x,shot.y);
            }),shots_.end());
        mission_.update(dt,x_,y_);
        ++frames_;
    }
    void render(uint32_t* pixels,size_t count) const {
        if(!pixels || count<static_cast<size_t>(WIDTH*HEIGHT))return;
        if(hasScene()) {
            std::copy(scene_.begin(),scene_.end(),pixels);
        } else {
        for(int y=0;y<HEIGHT;++y) for(int x=0;x<WIDTH;++x) {
            uint32_t noise=((uint32_t(x)*1664525u+uint32_t(y)*1013904223u)^seed_);
            noise^=noise>>15;noise*=2246822519u;noise^=noise>>13;
            const int shade=int(noise&15u);
            // Warm stylized terrain, deliberately original placeholder art.
            const int r=130+shade, g=105+shade, b=64+shade/2;
            pixels[y*WIDTH+x]=rgba(r,g,b);
        }
        for(int y=0;y<HEIGHT;++y)for(int x=0;x<WIDTH;++x){
            if(x>205+y/5 && x<237+y/5) pixels[y*WIDTH+x]=rgba(95,88,76);
            if(((x+y*2+int(seed_%19))%103)==0) pixels[y*WIDTH+x]=rgba(167,143,87);
        }
        disc(pixels,81,74,15,rgba(74,67,47));
        rect(pixels,70,61,91,70,rgba(136,119,86));
        rect(pixels,74,55,88,63,rgba(88,83,70));
        disc(pixels,264,168,17,rgba(72,65,48));
        rect(pixels,254,156,279,167,rgba(155,132,87));
        }
        // Original prototype targets are intentionally drawn above any imported
        // background. Baked vehicles in an AI concept image are NOT game entities.
        for(const auto& target:mission_.targets()){
            const int tx=int(target.x),ty=int(target.y);
            if(target.hp<=0){
                disc(pixels,tx,ty,10,rgba(53,45,35));
                disc(pixels,tx+2,ty-1,5,rgba(77,55,40));
                continue;
            }
            // Four distinct stationary ground targets; no licensed assets.
            rect(pixels,tx-12,ty-7,tx+13,ty+8,rgba(38,44,34));
            rect(pixels,tx-10,ty-6,tx+11,ty+6,
                 target.type==2?rgba(79,91,132):rgba(85,100,62));
            rect(pixels,tx-6,ty-4,tx+7,ty+5,rgba(132,128,77));
            disc(pixels,tx,ty,5,rgba(55,72,48));
            if(target.turret)
                line(pixels,tx,ty,tx,ty-11,rgba(34,36,33),2);
            rect(pixels,tx-10,ty-15,tx+10,ty-12,rgba(67,40,30));
            const int bar=target.hp*20/target.maxHp;
            rect(pixels,tx-10,ty-15,tx-10+bar,ty-12,rgba(239,91,53));
        }
        for(const auto& bullet:mission_.hostileShots()){
            disc(pixels,int(bullet.x),int(bullet.y),2,rgba(255,88,47));
        }
        for(const auto& blast:mission_.blasts()){
            const int radius=std::max(2,int(blast.ttl*19.f));
            disc(pixels,int(blast.x),int(blast.y),radius,rgba(238,130,45));
            disc(pixels,int(blast.x),int(blast.y),std::max(1,radius/2),rgba(255,218,108));
        }
        disc(pixels,int(x_)+5,int(y_)+13,17,rgba(67,61,49));
        // Helicopter shadow remains procedural. The optional RGBA sprite replaces
        // only the demonstration helicopter; it never changes gameplay mechanics.
        if (sprite_.valid()) {
            sprite_.draw(pixels, WIDTH, HEIGHT, int(x_), int(y_), heading_);
        } else {
            line(pixels,int(x_),int(y_)+3,int(x_),int(y_)+25,rgba(43,45,40),3);
            disc(pixels,int(x_),int(y_),10,rgba(38,50,47));
            disc(pixels,int(x_)-2,int(y_)-2,7,rgba(110,144,133));
            disc(pixels,int(x_)-3,int(y_)-3,3,rgba(170,190,184));
            rect(pixels,int(x_)-2,int(y_)+9,int(x_)+2,int(y_)+19,rgba(53,56,51));
            line(pixels,int(x_)-20,int(y_)-5,int(x_)+21,int(y_)+5,rgba(184,188,177),2);
        }
        for(const auto& shot:shots_) {
            disc(pixels,int(shot.x),int(shot.y),2,rgba(255,205,94));
        }
        // Minimal in-engine health bar and completion indicator.
        rect(pixels,7,8,110,17,rgba(30,31,29));
        rect(pixels,9,10,9+mission_.health(),15,
             mission_.health()>30?rgba(49,225,106):rgba(252,78,60));
        for(int i=0;i<mission_.total();++i){
            rect(pixels,8+i*13,23,18+i*13,28,
                i<mission_.destroyed()?rgba(73,219,101):rgba(220,75,54));
        }
        if(mission_.state()==CombatMission::State::Won){
            rect(pixels,0,0,WIDTH,3,rgba(31,226,105));
        } else if(mission_.state()==CombatMission::State::Lost){
            rect(pixels,0,0,WIDTH,3,rgba(251,72,56));
        }
    }
private:
    static uint32_t rgba(int r,int g,int b) {
        return 0xff000000u|(uint32_t(r)<<16)|(uint32_t(g)<<8)|uint32_t(b);
    }
    static void rect(uint32_t* dst,int ax,int ay,int bx,int by,uint32_t color){
        for(int y=std::max(0,ay);y<std::min(HEIGHT,by);++y)
            for(int x=std::max(0,ax);x<std::min(WIDTH,bx);++x)dst[y*WIDTH+x]=color;
    }
    static void disc(uint32_t* dst,int x,int y,int radius,uint32_t color){
        for(int yy=std::max(0,y-radius);yy<std::min(HEIGHT,y+radius+1);++yy)
            for(int xx=std::max(0,x-radius);xx<std::min(WIDTH,x+radius+1);++xx)
                if((xx-x)*(xx-x)+(yy-y)*(yy-y)<=radius*radius)dst[yy*WIDTH+xx]=color;
    }
    static void line(uint32_t* dst,int x0,int y0,int x1,int y1,uint32_t color,int radius){
        const int steps=std::max(std::abs(x1-x0),std::abs(y1-y0));
        for(int k=0;k<=steps;++k) {
            const int x=x0+(steps?(x1-x0)*k/steps:0);
            const int y=y0+(steps?(y1-y0)*k/steps:0);
            disc(dst,x,y,radius,color);
        }
    }
    SpriteImage sprite_;
    CombatMission mission_;
    std::vector<uint32_t> scene_;
    int heading_=0;
    bool ready_=false;
    uint32_t seed_=0;
    float x_=160,y_=135,fireCooldown_=0;
    uint64_t frames_=0;
    std::vector<Shot> shots_;
};
} // namespace romnative
