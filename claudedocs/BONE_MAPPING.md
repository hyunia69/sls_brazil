# Bone Mapping & Coordinate System Analysis

## 1. 본 이름 매핑 (3개 아바타 모델 간)

### 1.1 VLibras 애니메이션 ↔ VLibras FBX 아바타

**동일한 Unity 프로젝트 출처** → 본 이름 직접 매칭 (매핑 불필요)

FBXLoader는 본 이름을 그대로 보존 (점, 대시 포함):
```
Animation: Armature.001/BnBacia.001/BnCol-01/BnCol-02/BnCol-03/BnOmbro.L
FBX Bone Name: BnOmbro.L  ← leaf name으로 매칭
```

**주의**: GLB/glTF 변환 시 Blender가 `.`을 제거하여 `BnBacia.001` → `BnBacia001`으로 변경되는 문제 발생. FBXLoader 직접 사용으로 이 문제 해결.

### 1.2 VLibras ↔ ABNT avatarModel (참조용)

| VLibras (Portuguese) | ABNT avatarModel (English) | Body Part |
|---------------------|---------------------------|-----------|
| BnBacia.001 | hips_JNT | 골반 루트 |
| BnBacia | (no direct equiv) | 힙 |
| BnCol-01 | spine_JNT | 척추 1 |
| BnCol-02 | spine1_JNT | 척추 2 |
| BnCol-03 | spine2_JNT | 척추 3 |
| BnOmbro.L | l_shoulder_JNT | 왼쪽 어깨 |
| BnBraco.L | l_arm_JNT | 왼팔 |
| BnAntBraco.L | l_forearm_JNT | 왼 전완 |
| BnMao.L | l_hand_JNT | 왼손 |
| BnDedo.1.L | l_handThumb1_JNT | 왼 엄지 1 |
| BnDedo.1.L.001 | l_handIndex1_JNT | 왼 검지 1 |
| BnDedo.1.L.002 | l_handMiddle1_JNT | 왼 중지 1 |
| BnDedo.1.L.003 | l_handRing1_JNT | 왼 약지 1 |
| BnDedo.1.L.004 | l_handPinky1_JNT | 왼 소지 1 |
| BnPescoco | neck_JNT | 목 |
| BnCabeca | head_JNT | 머리 |
| BnBacia_L | l_upleg_JNT | 왼쪽 대퇴 |
| BnPerna.L | l_leg_JNT | 왼쪽 하퇴 |

**차이점**:
- VLibras: 84본, BnAntBraco.L.001 같은 추가 보조 본 존재
- ABNT: 41본 (93 노드 중), 더 단순한 계층
- VLibras: 얼굴 본 풍부 (눈꺼풀, 혀, 볼, 눈썹 등)
- ABNT: 얼굴 본 제한적 (눈, 머리만)
- VLibras: 손가락 각 3 phalanges
- ABNT: 손가락 각 4 JNT (Thumb1~4)

### 1.3 손가락 본 매핑 상세

**VLibras 손가락 구조** (왼손 예시):
```
BnMao.L (hand)
├── BnDedo.1.L (thumb proximal)
│   └── BnDedo.1.L.006 (thumb middle)
│       └── BnDedo.1.L.005 (thumb distal)
├── BnDedo.1.L.001 (index proximal)
│   └── BnDedo.1.L.008 (index middle)
│       └── BnDedo.1.L.007 (index distal)
├── BnDedo.1.L.002 (middle proximal)
│   └── BnDedo.1.L.010 (middle middle)
│       └── BnDedo.1.L.009 (middle distal)
├── BnDedo.1.L.003 (ring proximal)
│   └── BnDedo.1.L.012 (ring middle)
│       └── BnDedo.1.L.011 (ring distal)
└── BnDedo.1.L.004 (pinky proximal)
    └── BnDedo.1.L.014 (pinky middle)
        └── BnDedo.1.L.013 (pinky distal)
```

## 2. 좌표계 분석

### 2.1 좌표 시스템 비교
| System | Handedness | Up | Forward | Right |
|--------|-----------|-----|---------|-------|
| Unity | Left-handed | +Y | +Z | +X |
| Three.js | Right-handed | +Y | -Z | +X |
| FBX (default) | Right-handed | +Y | +Z | +X |
| glTF | Right-handed | +Y | +Z | +X |

### 2.2 변환 규칙

**Unity → Three.js (직접)**:
- Position: `(x, y, z)` → `(x, y, -z)`
- Quaternion: `(x, y, z, w)` → `(x, y, -z, -w)` 또는 `(-x, -y, z, w)` (동등)

**FBXLoader 내부 처리**:
- FBXLoader는 FBX 파일의 UpAxis/FrontAxis 메타데이터를 읽음
- Unity 내보낸 FBX: Y-up → FBXLoader가 루트 레벨 보정 적용
- 결과적으로 본의 local quaternion은 대체로 보존됨

### 2.3 이전 시도 실패 분석

```
경로A (애니메이션): Unity JSON → Python [-x,-y,z,w] → glTF
경로B (아바타):     Unity FBX → Blender (auto_orient=False) → GLB

문제: 두 경로가 서로 다른 변환을 적용
→ 상체 (W > 0인 본): 우연히 정상
→ 하체 (W < 0인 본): 회전 반전
```

| 본 | Unity W값 | 증상 |
|---|-----------|------|
| BnOmbro.L | +양수 | 정상 |
| BnBraco.L | +양수 | 정상 |
| BnBacia | ~0 | 왜곡 |
| BnBacia_L | -0.4945 | 심한 왜곡 |

### 2.4 새로운 접근: FBXLoader 직접 사용

```
신규 단일 파이프라인:
Unity JSON → JS 직접 파싱 → AnimationClip
FBX 아바타 → FBXLoader → Scene

두 소스가 동일한 Unity 좌표계에서 출발
→ FBXLoader의 내부 변환만 고려하면 됨
```

**검증 결과 (2026-04-01)**:
- FBXLoader는 본 quaternion의 Y, Z 성분을 반전하여 저장
- **YZ-negate 변환이 정답**: `[x, -y, -z, w]`
- 83개 본 중 65개 YZ-negate 매칭, 13개 identity 매칭 (Y,Z가 0인 본), 5개 근사 매칭

### 2.5 FBXLoader 본 이름 변환 (중요)

FBXLoader는 본 이름에서 `.`을 제거:
```
Animation: BnBacia.001 → FBX: BnBacia001
Animation: BnOmbro.L → FBX: BnOmbroL
Animation: BnDedo.1.L.001 → FBX: BnDedo1L001
```
`-`는 보존: `BnCol-01` → `BnCol-01`

**해결**: `normalizeBoneName(name) { return name.replace(/\./g, ''); }`

### 2.6 FBXLoader 중첩 스켈레톤 구조 (치명적 발견)

FBXLoader는 다중 SkinnedMesh FBX 파일에서 **중첩 본 체인**을 생성:
```
BnOmbroL
└── BnBracoL (skeleton 1의 본)
    ├── BnAntBracoL
    └── BnBracoL (skeleton 2의 본)
        └── BnBracoL (skeleton 3의 본)
            └── ... (10개 스켈레톤 × 90본)
```

각 SkinnedMesh는 자신의 스켈레톤 인스턴스를 가지며, 동일 이름의 본이
중첩되어 있어 동일 quaternion을 모든 인스턴스에 설정하면 **회전이 누적**됨.

**해결**:
1. "Primary bone" = 부모 이름이 다른 본 (innermost, 실제 armature 계층의 본)
2. "Passthrough bones" = 부모 이름이 같은 본 (중첩 복사본)
3. Passthrough bones는 **FBX 원래 값 유지** (identity로 변경하면 bind pose 불일치 발생)
4. Primary bone만 애니메이션 적용
5. `calculateInverses()` 호출하지 않음 - FBXLoader의 원래 bind matrices 유지
6. Compounding은 skinning equation에서 자동 취소됨 (delta = bone.world × inverse(bone.bind_world))

### 2.5 Scale 이슈

Position 값 비교:
- CASA JSON `BnBacia.001` position: `[0, -0.00893, 0]` (미터)
- FBX 아바타 본 position: 확인 필요 (FBX는 보통 cm 단위)
- 예상 scale factor: ×100 (meters → cm)

## 3. Bind Pose 문제 (핵심)

### 3.1 문제 설명
```
SkinnedMesh 변형 공식:
vertexWorldPos = bindMatrix × boneInverse[i] × boneWorldMatrix × vertexLocalPos

boneInverse[i]는 bind 시점의 bone world transform의 역행렬
→ 애니메이션의 reference pose ≠ bind pose이면 vertex가 발산
```

### 3.2 해결 전략
```javascript
// 1. FBX 로드
const model = await loadFBX('Icaro.fbx');

// 2. 애니메이션 frame-0를 모든 본에 적용
applyFrame0(model, casaData);

// 3. 세계 행렬 업데이트
model.updateMatrixWorld(true);

// 4. Bind pose 재계산
model.traverse(obj => {
    if (obj.isSkinnedMesh) {
        obj.skeleton.calculateInverses();
        obj.frustumCulled = false;
    }
});

// 5. 이후 정상 재생
const mixer = new THREE.AnimationMixer(model);
mixer.clipAction(clip).play();
```

### 3.3 FBXLoader preRotation

FBXLoader는 FBX의 PreRotation 속성을 `bone.userData.preRotation`에 저장하고 본의 quaternion에 적용.

애니메이션 데이터가 preRotation을 포함하지 않는 경우:
```javascript
// preRotation 보정이 필요한지 확인
model.traverse(bone => {
    if (bone.isBone && bone.userData.preRotation) {
        console.log(bone.name, 'preRotation:', bone.userData.preRotation);
    }
});
```

필요 시 애니메이션 quaternion에 preRotation의 역을 곱하여 보정.
