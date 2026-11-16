"""Testes de contrato da sincronização da miniatura sem dependência Three.js."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'aplicar-miniatura-sync.py'
spec = importlib.util.spec_from_file_location('rd_mini_sync_patch', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

MOCK = '''let mini=null;
function createMiniGraph(){
 miniCamera.position.set(0,0,13.8);
 const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();let down=null;
 canvas.addEventListener('pointerdown',e=>{e.stopPropagation();down={x:e.clientX,y:e.clientY,sx:e.clientX,sy:e.clientY,moved:false};canvas.setPointerCapture(e.pointerId)});
 canvas.addEventListener('pointermove',e=>{if(!down)return;e.stopPropagation();const dx=e.clientX-down.x,dy=e.clientY-down.y;if(Math.abs(e.clientX-down.sx)+Math.abs(e.clientY-down.sy)>6)down.moved=true;assembly.rotation.y+=dx*.012;assembly.rotation.x+=dy*.012;down.x=e.clientX;down.y=e.clientY});
 canvas.addEventListener('pointerup',e=>{e.stopPropagation();if(!down)return;const moved=down.moved;down=null;if(moved)return;const r=canvas.getBoundingClientRect();mouse.set((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height*2-1));ray.setFromCamera(mouse,miniCamera);const hit=ray.intersectObjects(nodes,false)[0];if(hit)travel(hit.object.userData.index)});
 canvas.addEventListener('pointercancel',()=>{down=null});
 canvas.addEventListener('wheel',e=>{e.preventDefault();e.stopPropagation();miniCamera.position.z=Math.max(9,Math.min(21,miniCamera.position.z+Math.sign(e.deltaY)*.8))},{passive:false});
 function size(){}
 return {render(dt){if(!down)assembly.rotation.y+=dt*.075;nodes.forEach(x=>x.rotation.y+=dt*.18);}};
}
function arrange(){w.goalPosition=center.clone().add(new THREE.Vector3(6.2*Math.cos(angle),4.85*Math.sin(angle),-3.5));}
function loop(){if(auto&&!drag&&!document.hidden){} }
'''


class MiniSyncTests(unittest.TestCase):
    def test_contract(self):
        new = module.transform(MOCK)
        self.assertIn('miniInteracting',new)
        self.assertIn('const miniPose={yaw:0,pitch:0}',new)
        self.assertIn("canvas.addEventListener('lostpointercapture'",new)
        self.assertIn('fingers.size===2',new)
        self.assertIn('transition=null;',new)
        self.assertIn('w.group.position.copy(w.goalPosition)',new)
        self.assertIn('if(auto&&!drag&&!miniInteracting&&!document.hidden)',new)
        self.assertIn('if(hit)travel(hit.object.userData.index)',new)
        self.assertEqual(module.transform(new),new)

    def test_adapted_configuration_is_not_replaced(self):
        before = "const rdCfg=(key,fallback)=>fallback;\n" + MOCK
        after = module.transform(before)
        self.assertIn('const rdCfg=(key,fallback)=>fallback;',after)
        self.assertIn("rdCfg('zoomMin',.72)",after)
        self.assertIn("rdCfg('dragSensitivity',.008)",after)

    def test_unknown_event_extra_is_rejected(self):
        changed=MOCK.replace(' function size(){}'," canvas.addEventListener('dblclick',()=>{});\n function size(){}")
        with self.assertRaisesRegex(ValueError,'alterados por outro patch'):
            module.transform(changed)

    def test_unknown_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'miniatura'):
            module.transform('console.log("motor novo");')

if __name__=='__main__':unittest.main()
