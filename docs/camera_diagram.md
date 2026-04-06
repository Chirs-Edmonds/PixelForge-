# PixelForge — Isometric Camera Reference

## Angle Mathematics

```
True isometric elevation = arctan(1 / sqrt(2)) = 35.264°

Camera orbits the mesh center on a sphere of radius 6 Blender units.
Elevation is constant at 35.264°. Azimuth steps 45° per direction.

Z (height) is the same for all directions:
  Z = 6 * sin(35.264°) = 3.464 Blender units

Horizontal orbit radius:
  R = 6 * cos(35.264°) = 4.899 Blender units
```

## Direction → Camera Position (relative to mesh center, distance=6)

| Direction | Azimuth | Camera X | Camera Y  | Camera Z |
|-----------|---------|----------|-----------|----------|
| N         |   0°    |  0.000   | -4.899    | 3.464    |
| NE        |  45°    |  3.464   | -3.464    | 3.464    |
| E         |  90°    |  4.899   |  0.000    | 3.464    |
| SE        | 135°    |  3.464   |  3.464    | 3.464    |
| S         | 180°    |  0.000   |  4.899    | 3.464    |
| SW        | 225°    | -3.464   |  3.464    | 3.464    |
| W         | 270°    | -4.899   |  0.000    | 3.464    |
| NW        | 315°    | -3.464   | -3.464    | 3.464    |

## Coordinate Convention

```
Blender +Y = game "North"
Azimuth 0° (North): camera sits at -Y, looks toward +Y
Azimuth increases clockwise when viewed from above (game-standard CW from North)

Position formulas:
  x = dist * cos(elev) * sin(az)
  y = -dist * cos(elev) * cos(az)   ← negative: 0°=North maps to -Y axis
  z = dist * sin(elev)
```

## Sprite Sheet Direction Order

```
[N][NE][E][SE][S][SW][W][NW]
 0   1  2   3  4   5  6   7   ← column index
```

Each frame is `SPRITE_SIZE × SPRITE_SIZE` pixels.
Total sheet width: `8 × SPRITE_SIZE` pixels.
