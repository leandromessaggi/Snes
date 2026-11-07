import copy
import json
import unittest
from rom2native.mission_schema import validate_bytes,ROM_SHA

SAMPLE={
    "format":"rom2native-mission-v1","rom_sha256":ROM_SHA,
    "title":"Test mission","goal":"destroy_all",
    "targets":[
        {"id":"tower1","type":"turret","x":70,"y":80,"hp":3},
        {"id":"patrol1","type":"patrol","x":200,"y":160,"hp":2,"patrol_range":20},
        {"id":"depot","type":"depot","x":140,"y":190,"hp":1}
    ]
}
def pack(d):return json.dumps(d).encode("utf-8")

class MissionSchemaTests(unittest.TestCase):
    def test_valid_profile(self):
        result=validate_bytes(pack(SAMPLE))
        self.assertEqual(result["target_count"],3)
        self.assertEqual(result["types"],{"depot":1,"turret":1,"patrol":1})
    def test_bad_hash(self):
        p=copy.deepcopy(SAMPLE);p["rom_sha256"]="a"*64
        with self.assertRaises(ValueError):validate_bytes(pack(p))
    def test_no_targets(self):
        p=copy.deepcopy(SAMPLE);p["targets"]=[]
        with self.assertRaises(ValueError):validate_bytes(pack(p))
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate_bytes(b'{"format":"x","format":"y"}')
    def test_overlapping_targets(self):
        p=copy.deepcopy(SAMPLE)
        p["targets"][1].update(x=74,y=82)
        with self.assertRaises(ValueError):validate_bytes(pack(p))
    def test_invalid_patrol_range(self):
        p=copy.deepcopy(SAMPLE);p["targets"][1]["patrol_range"]=0
        with self.assertRaises(ValueError):validate_bytes(pack(p))
    def test_boolean_is_not_int(self):
        p=copy.deepcopy(SAMPLE);p["targets"][0]["hp"]=True
        with self.assertRaises(ValueError):validate_bytes(pack(p))
    def test_large_input(self):
        with self.assertRaises(ValueError):validate_bytes(b" "*32769)
    def test_too_many_targets(self):
        p=copy.deepcopy(SAMPLE)
        p["targets"]=[dict(id=f"target{i}",type="depot",x=50,y=50,hp=1) for i in range(13)]
        with self.assertRaises(ValueError):validate_bytes(pack(p))

if __name__=="__main__":unittest.main()
