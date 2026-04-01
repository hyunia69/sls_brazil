# Previous Attempts Analysis

## 1. 이전 구현 기록

### 1.1 프로젝트 위치
`D:\lg\work\SLS\brazil\code\player\` - 별도 디렉토리에서 작업

### 1.2 구현된 플레이어들
| 플레이어 | 상태 | 방식 |
|---------|------|------|
| player_bvh | 완료 | BVH 전용 재생 |
| player_bvh_slmb | 완료 | SLMB 파이프라인 검증 |
| player_vlibras | 진행중 | GLB 아바타 + glTF 애니메이션 |
| player_vlibras_anti | 진행중 | 대안 접근 (world-space retargeting) |

### 1.3 ABNT 축 (완료)
- SLMB 인코딩/디코딩/재생 파이프라인 전체 검증 완료
- BVH → SLMB → Three.js 재생 성공
- ABNT NBR 25606 표준 준수

## 2. VLibras 플레이어 실패 분석

### 2.1 근본 원인: 이중 파이프라인 좌표 변환 불일치

```
경로A (애니메이션):
Unity AssetBundle → extract_casa.py (UnityPy) → CASA_full.json
→ vlibras_to_gltf.py (Python) → CASA_vlibras.gltf
→ 변환: quaternion [-x, -y, z, w]

경로B (아바타):
Unity FBX → Blender import (axis_forward=-Z, axis_up=Y, auto_orient=False)
→ Blender GLB export (export_yup=True)
→ Icaro.glb

문제: 경로A와 경로B의 좌표 변환이 다름
```

### 2.2 증상

**스켈레톤만 재생**: 정상 (본 위치/회전 시각적으로 올바름)

**아바타에 적용 시**:
- 상체: 우연히 정상 (W값이 양수인 본들)
- 하체: 심한 왜곡 (W값이 음수인 본들 - BnBacia, BnBacia_L)
- mesh가 발산하거나 반전됨

### 2.3 디버깅 과정 (수십 장의 스크린샷)

```
player/ 디렉토리에 70+ 스크린샷 존재:
- vlibras_dirA_*.png - 방향A 변환 시도
- vlibras_v2_*.png - v2 모드 시도
- compare_*.png - 비교 이미지
- worldspace_*.png - world-space retargeting 시도
- final_*.png - 최종 결과
- bone_reset_test.png - 본 리셋 테스트
```

### 2.4 시도된 변환 공식들

1. **직접 복사** `[x, y, z, w]`: 하체 즉시 왜곡
2. **Z-flip** `[-x, -y, z, w]`: 상체 정상, 하체 왜곡
3. **W-normalize + Z-flip**: 부분적 개선, 완전한 해결 아님
4. **Z-negate** `[x, y, -z, w]`: 전체적으로 어긋남

### 2.5 World-Space Retargeting (player_vlibras_anti)
- 아바타의 rest pose와 애니메이션의 rest pose 차이를 delta로 계산
- 매 프레임마다 delta를 적용하여 world-space에서 재타겟팅
- 결과: 부분적 성공, 그러나 Blender FBX import의 bone roll 조정이 예측 불가

## 3. 핵심 교훈

### 3.1 실패한 접근 (하지 말 것)
1. **두 개의 다른 파이프라인을 맞추려는 시도** - 근본적으로 취약
2. **GLB 중간 변환** - Blender가 본 이름과 좌표를 예측 불가능하게 변경
3. **점진적 패치** - 개별 본 보정은 임시방편, 새 데이터에서 다시 깨짐
4. **하체 필터링** - 증상을 숨기는 것, 근본 해결 아님

### 3.2 발견된 해결 방향
1. **단일 파이프라인**: FBXLoader로 아바타를 직접 로드 (Blender 변환 제거)
2. **JSON 직접 파싱**: glTF 중간 변환 없이 JS에서 AnimationClip 빌드
3. **Bind Pose 보정**: `skeleton.calculateInverses()` 호출
4. **preRotation 확인**: FBXLoader가 추가하는 preRotation 보정

### 3.3 가져갈 코드/패턴
- `extract_casa.py`: AssetBundle → JSON 추출 (UnityPy) - 작동함
- `avatars/vlibras/index.html`: FBX 뷰어 - Three.js FBXLoader 패턴
- AnimationClip 빌드 로직 (`buildClipFromJSON`)
- UI 패턴 (재생 컨트롤, 스켈레톤 오버레이)

## 4. 새 접근법의 차이점

| 항목 | 이전 (실패) | 신규 (계획) |
|------|-----------|-----------|
| 아바타 포맷 | GLB (Blender 변환) | FBX (직접 FBXLoader) |
| 애니메이션 소스 | glTF (Python 변환) | JSON (JS 직접 파싱) |
| 좌표 변환 | 이중 파이프라인 | 단일 파이프라인 |
| 본 이름 | `.` 제거됨 (Blender) | `.` 보존 (FBXLoader) |
| Bind pose | 미처리 | calculateInverses() |
| 하체 처리 | 필터링 (회피) | 올바른 변환으로 근본 해결 |
| Scale | 100x 불일치 | FBX 네이티브 단위 |
