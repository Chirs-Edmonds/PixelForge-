@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM ============================================================
REM  PixelForge — Phase 1 Pipeline Runner
REM  Renders 8 isometric directions in Blender, then assembles
REM  into a sprite sheet using Pillow.
REM
REM  Usage:
REM    run_pipeline.bat
REM
REM  To use a custom .glb mesh, uncomment the MESH_ARG line below.
REM ============================================================

SET BLENDER="C:\Program Files\Blender Foundation\Blender 4.x\blender.exe"
SET PYTHON="C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"

SET BAKE_SCRIPT=%~dp0scripts\blender_bake.py
SET ASSEMBLE_SCRIPT=%~dp0scripts\assemble_sheet.py
SET OUTPUT_FRAMES=%~dp0output\frames
SET OUTPUT_SHEET=%~dp0output\sprite_sheet.png

REM ---- SIZE CONFIGURATION ----
REM Change SPRITE_SIZE to control output resolution.
REM Common values: 16, 32, 64, 128, 256
SET SPRITE_SIZE=64
SET /A RENDER_SIZE=SPRITE_SIZE*4

REM ---- MESH INPUT ----
REM Leave MESH_ARG empty to use the built-in humanoid test primitive.
REM Uncomment and edit the next line to use a .glb file:
REM SET MESH_ARG=--mesh "%~dp0assets\your_mesh.glb"
SET MESH_ARG=

REM ============================================================

echo.
echo  PixelForge Pipeline
echo  Sprite size : %SPRITE_SIZE%x%SPRITE_SIZE%px
echo  Render size : %RENDER_SIZE%x%RENDER_SIZE%px (internal)
IF DEFINED MESH_ARG (
    echo  Mesh        : %MESH_ARG%
) ELSE (
    echo  Mesh        : (test primitive - humanoid capsule)
)
echo.

REM ------------------------------------------------------------
REM  Step 1: Blender headless render
REM ------------------------------------------------------------
echo [Step 1/2] Blender headless render ^(8 directions^)...
echo.

%BLENDER% --background --factory-startup --python "%BAKE_SCRIPT%" -- ^
    --outdir "%OUTPUT_FRAMES%" ^
    --size %RENDER_SIZE% ^
    %MESH_ARG%

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Blender render failed. See output above.
    echo  Check that Blender is installed at:
    echo    C:\Program Files\Blender Foundation\Blender 4.x\blender.exe
    EXIT /B 1
)

REM ------------------------------------------------------------
REM  Step 2: Assemble sprite sheet
REM ------------------------------------------------------------
echo.
echo [Step 2/2] Assembling sprite sheet...
echo.

%PYTHON% "%ASSEMBLE_SCRIPT%" ^
    --framesdir "%OUTPUT_FRAMES%" ^
    --outfile "%OUTPUT_SHEET%" ^
    --size %SPRITE_SIZE%

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Sprite sheet assembly failed.
    echo  Make sure Pillow is installed:
    echo    py -3.12 -m pip install Pillow
    EXIT /B 1
)

echo.
echo  Done! Output: %OUTPUT_SHEET%
echo.

ENDLOCAL
