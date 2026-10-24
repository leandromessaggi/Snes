// Deterministic Libretro mock. Contains no commercial ROM or game assets.
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <array>
#include <algorithm>

extern "C" {
struct retro_game_info { const char* path; const void* data; size_t size; const char* meta; };
struct retro_geometry { unsigned base_width, base_height, max_width, max_height; float aspect_ratio; };
struct retro_timing { double fps, sample_rate; };
struct retro_system_av_info { retro_geometry geometry; retro_timing timing; };
using env_t = bool (*)(unsigned, void*);
using video_t = void (*)(const void*, unsigned, unsigned, size_t);
using sample_t = void (*)(int16_t, int16_t);
using batch_t = size_t (*)(const int16_t*, size_t);
using poll_t = void (*)();
using input_t = int16_t (*)(unsigned, unsigned, unsigned, unsigned);
}
namespace {
env_t env{}; video_t video{}; sample_t audio{}; batch_t batch{};
poll_t poll{}; input_t input{};
unsigned format{}; unsigned frames{};
std::array<uint8_t,1024> wram{};
std::array<uint8_t,16> sram{};
}
extern "C" {
void retro_set_environment(env_t f) { env=f; }
void retro_set_video_refresh(video_t f) { video=f; }
void retro_set_audio_sample(sample_t f) { audio=f; }
void retro_set_audio_sample_batch(batch_t f) { batch=f; }
void retro_set_input_poll(poll_t f) { poll=f; }
void retro_set_input_state(input_t f) { input=f; }
void retro_init() {}
void retro_deinit() {}
bool retro_load_game(const retro_game_info* g) {
    if (!g || !g->data || g->size<16 || !env || !video || !audio || !batch || !input || !poll) return false;
    format=static_cast<const uint8_t*>(g->data)[0];
    if(format>2 || !env(10,&format)) return false;
    frames=0; wram.fill(0); sram.fill(0); return true;
}
void retro_unload_game() {}
void retro_set_controller_port_device(unsigned,unsigned) {}
void retro_get_system_av_info(retro_system_av_info* av) {
    *av={{2,2,2,2,4.0f/3.0f},{60.0,32000.0}};
}
void retro_run() {
    poll();
    const uint16_t buttons=static_cast<uint16_t>(input(0,1,0,256));
    wram[0]=static_cast<uint8_t>(buttons);
    wram[1]=static_cast<uint8_t>(buttons>>8);
    wram[2]=static_cast<uint8_t>(++frames);
    if(format==1) {
        const uint32_t pix[4]={0x00ff0000,0x0000ff00,0x000000ff,0x00ffffff};
        video(pix,2,2,8);
    } else {
        const uint16_t rgb555[4]={0x7c00,0x03e0,0x001f,0x7fff};
        const uint16_t rgb565[4]={0xf800,0x07e0,0x001f,0xffff};
        video(format==2?rgb565:rgb555,2,2,4);
    }
    const int16_t s[]={-1,1,-100,100,-32768,32767,0,0};
    batch(s,4);
    audio(-123,456);
}
struct MockState { uint32_t frame; uint8_t wram[1024]; uint8_t sram[16]; };
size_t retro_serialize_size() { return sizeof(MockState); }
bool retro_serialize(void* out,size_t n) {
    if(!out || n!=sizeof(MockState)) return false;
    MockState x{};
    x.frame=frames;
    std::copy(wram.begin(),wram.end(),x.wram);
    std::copy(sram.begin(),sram.end(),x.sram);
    std::memcpy(out,&x,sizeof(x)); return true;
}
bool retro_unserialize(const void* ptr,size_t n) {
    if(!ptr || n!=sizeof(MockState)) return false;
    MockState x{};
    std::memcpy(&x,ptr,sizeof(x));
    frames=x.frame;
    std::copy(x.wram,x.wram+1024,wram.begin());
    std::copy(x.sram,x.sram+16,sram.begin());
    return true;
}
void* retro_get_memory_data(unsigned id) { return id==2?wram.data():id==0?sram.data():nullptr; }
size_t retro_get_memory_size(unsigned id) { return id==2?wram.size():id==0?sram.size():0; }
}
