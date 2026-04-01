# Implementation Plan - VLibras Three.js Player

## Phase 1: Python 전처리 파이프라인 (1일)

### 1.1 `tools/extract_animation.py`
기존 `player/data/CASA/extract_casa.py`를 강화:

```python
# 추가 기능:
# 1. tangent 데이터 포함 (inSlope, outSlope, inWeight, outWeight)
# 2. 30FPS 프리베이크 모드 (--prebake)
# 3. float curve attribute name 추출
# 4. scale curve bone path 추출
# 5. 배치 모드 (--batch, VLibras CDN)
# 6. 출력 JSON 스키마 표준화
```

### 1.2 출력 확인
- CASA_full.json이 모든 curve 타입을 포함하는지 확인
- 프리베이크 모드에서 30FPS 균등 샘플링 확인
- 다른 AssetBundle 단어로 테스트

## Phase 2: 핵심 플레이어 구현 (2-3일) ★

### 2.1 FBX 아바타 로딩
```javascript
// avatars/vlibras/index.html 패턴 재활용
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';

const AVATARS = {
    icaro: { fbx: '../avatars/vlibras/icaro/Icaro_NovoEstilo.fbx', textures: {...} },
    hozana: { fbx: '../avatars/vlibras/hozana/Hozana2.0.fbx', textures: {...} },
    guga: { fbx: '../avatars/vlibras/guga/GuGa.fbx', textures: {...} }
};
```

### 2.2 디버그 로깅 (중요)
로딩 직후:
```javascript
model.traverse(bone => {
    if (bone.isBone) {
        console.log(`BONE: ${bone.name}`,
            'quat:', bone.quaternion.toArray(),
            'pos:', bone.position.toArray(),
            'scale:', bone.scale.toArray(),
            'preRot:', bone.userData.preRotation || 'none'
        );
    }
});
```

### 2.3 JSON 파싱 + Bone Map 매칭
```javascript
async function loadAnimation(url) {
    const json = await fetch(url).then(r => r.json());

    // bone_paths에서 leaf name 추출
    const animBones = json.bone_paths.map(p => p.split('/').pop());

    // FBX 모델의 본과 비교
    const fbxBones = [];
    model.traverse(b => { if (b.isBone) fbxBones.push(b.name); });

    // 매칭 로그
    const matched = animBones.filter(n => fbxBones.includes(n));
    const unmatched = animBones.filter(n => !fbxBones.includes(n));
    console.log('Matched:', matched.length, 'Unmatched:', unmatched);

    return json;
}
```

### 2.4 좌표 변환 실험 UI
```javascript
const CONVERSIONS = {
    'identity': (q) => [q[0], q[1], q[2], q[3]],
    'z-flip': (q) => [-q[0], -q[1], q[2], q[3]],
    'w-norm-z-flip': (q) => {
        let [x,y,z,w] = q;
        if (w < 0) { x=-x; y=-y; z=-z; w=-w; }
        return [-x, -y, z, w];
    },
    'z-negate': (q) => [q[0], q[1], -q[2], q[3]]
};
// 드롭다운으로 선택, 즉시 반영
```

### 2.5 Bind Pose 보정 (★ 핵심)
```javascript
function calibrateBindPose(model, animData, convFn) {
    // 1. frame-0의 rotation을 모든 본에 적용
    for (const rc of animData.rotation_curves) {
        const boneName = rc.path.split('/').pop();
        const bone = boneMap[boneName];
        if (!bone) continue;

        const kf0 = rc.keyframes[0];
        const [qx, qy, qz, qw] = convFn(kf0.value);
        bone.quaternion.set(qx, qy, qz, qw);
    }

    // 2. 세계 행렬 강제 업데이트
    model.updateMatrixWorld(true);

    // 3. Bind pose 재계산
    model.traverse(obj => {
        if (obj.isSkinnedMesh) {
            obj.skeleton.calculateInverses();
            obj.frustumCulled = false;
        }
    });
}
```

### 2.6 AnimationClip 빌드 + 재생
```javascript
function buildAndPlay(animData, convFn) {
    const AUX = ['BnMaoOrient', 'BnPolyV', 'ik_FK'];
    const tracks = [];

    for (const rc of animData.rotation_curves) {
        const boneName = rc.path.split('/').pop();
        if (AUX.some(p => boneName.startsWith(p))) continue;
        if (!boneMap[boneName]) continue;

        const times = rc.keyframes.map(kf => kf.time);
        const values = rc.keyframes.flatMap(kf => convFn(kf.value));

        tracks.push(new THREE.QuaternionKeyframeTrack(
            boneName + '.quaternion',
            new Float32Array(times),
            new Float32Array(values)
        ));
    }

    const clip = new THREE.AnimationClip(animData.name, -1, tracks);
    const mixer = new THREE.AnimationMixer(model);
    const action = mixer.clipAction(clip);
    action.play();

    return mixer;
}
```

## Phase 3: UI 컨트롤 (1일)

### 3.1 재생 컨트롤
- Play/Pause (Space 키)
- Stop (S 키)
- 속도 제어 슬라이더 (0.1x ~ 5.0x)
- 타임라인 스크러버 (프레임 단위)
- 프레임 넘기기 (← →)

### 3.2 뷰 컨트롤
- OrbitControls (마우스 드래그)
- 스켈레톤 오버레이 토글
- 메쉬 표시/숨기기
- 와이어프레임 토글
- 그리드 토글

### 3.3 아바타 관리
- 3개 아바타 버튼 (Icaro/Hozana/Guga)
- 텍스처 토글
- 모델 정보 패널 (본 수, 메쉬 수, 정점 수)

### 3.4 디버그 패널
- 변환 공식 선택 드롭다운
- 현재 프레임/시간 표시
- 선택된 본의 quaternion/position 표시
- Console 로그 출력

## Phase 4: 순차 단어 재생 (1-2일)

### 4.1 단어 큐 시스템
```javascript
class SignPlayer {
    constructor(model, boneMap) {
        this.mixer = new THREE.AnimationMixer(model);
        this.queue = [];
        this.currentAction = null;
    }

    async playSequence(words) {
        for (const word of words) {
            const animData = await this.loadAnimation(word);
            const clip = this.buildClip(animData);
            await this.playClipWithTransition(clip);
        }
    }

    playClipWithTransition(clip, fadeDuration = 0.3) {
        const newAction = this.mixer.clipAction(clip);
        if (this.currentAction) {
            this.currentAction.crossFadeTo(newAction, fadeDuration);
        }
        newAction.play();
        this.currentAction = newAction;

        return new Promise(resolve => {
            this.mixer.addEventListener('finished', resolve);
        });
    }
}
```

### 4.2 애니메이션 캐시
```javascript
const animCache = new Map(); // word -> animData
async function getAnimation(word) {
    if (!animCache.has(word)) {
        const data = await fetch(`../animations/${word}_full.json`).then(r => r.json());
        animCache.set(word, data);
    }
    return animCache.get(word);
}
```

## Phase 5: 고급 기능 (이후)

### 5.1 Position 트랙
- FBX 아바타의 본 position 스케일 확인
- Scale factor 결정 (아마 ×100 meters→cm)
- VectorKeyframeTrack 추가

### 5.2 Float Curves → Morph Targets
- FBX 모델의 morph target 확인
- Unity float curve attribute name → morph target name 매핑
- NumberKeyframeTrack으로 적용

### 5.3 Scale Curves
- 84개 scale curve의 bone path 식별
- 얼굴 표정 본 scale 적용

### 5.4 다중 아바타 모델
- ABNT avatarModel (GLTF): GLTFLoader + bone name mapping
- PC Model (GLB): GLTFLoader + bone name mapping
- 매핑 테이블: `BONE_MAPPING.md` 참조

### 5.5 VLibras CDN 연동
- 실시간 AssetBundle 다운로드
- 브라우저 내 UnityFS 파싱 (큰 작업, 낮은 우선순위)
- 또는 서버 사이드 Python 추출 + REST API

## 검증 체크리스트

### Phase 2 (핵심)
- [ ] Icaro FBX 로드 성공 (텍스처 포함)
- [ ] CASA_full.json 파싱 성공 (84 bone paths)
- [ ] FBX 본 이름 ↔ JSON 본 이름 매칭 확인
- [ ] Armature.001 rest pose 비교 (FBX vs JSON frame-0)
- [ ] 4가지 변환 공식 시각적 비교
- [ ] Bind pose 보정 후 mesh 왜곡 없음
- [ ] 전체 애니메이션 재생 - 상체 정상
- [ ] 전체 애니메이션 재생 - 하체 정상
- [ ] 스켈레톤 모드에서 확인

### Phase 3
- [ ] Play/Pause/Stop 동작
- [ ] 속도 제어 동작
- [ ] 타임라인 스크러버 동작
- [ ] 3개 아바타 전환 정상
- [ ] 스켈레톤 오버레이 정상

### Phase 4
- [ ] 2개 단어 순차 재생
- [ ] 전환 블렌딩 부드러움
- [ ] 애니메이션 캐시 작동
