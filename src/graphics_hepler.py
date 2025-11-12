# src/graphics_helper.py
import json
from typing import List, Tuple  # <-- Make sure this is imported
from loguru import logger       # <-- Make sure this is imported


class SvgCoordinator:
    """
    Handles converting CIE xy coordinates to SVG pixel coordinates
    based on the provided background image dimensions and axis calibration.
    """
    def __init__(self):
        # X-axis data (CIE X: 0.0 to 0.8)
        self.X_PIXEL_START_CIE_0_0 = 47
        self.X_PIXEL_LENGTH = 408
        self.X_PIXEL_END_CIE_0_8 = self.X_PIXEL_START_CIE_0_0 + self.X_PIXEL_LENGTH

        # Y-axis data (CIE Y: 0.0 to 0.9)
        self.Y_PIXEL_START_CIE_0_9 = 32
        self.Y_PIXEL_LENGTH = 460
        self.Y_PIXEL_END_CIE_0_0 = self.Y_PIXEL_START_CIE_0_9 + self.Y_PIXEL_LENGTH

        # CIE data limits
        self.X_CIE_MIN = 0.0
        self.X_CIE_MAX = 0.8
        self.Y_CIE_MIN = 0.0
        self.Y_CIE_MAX = 0.9

        # Calculate pixels per CIE unit
        self.PIXELS_PER_CIE_X = self.X_PIXEL_LENGTH / (self.X_CIE_MAX - self.X_CIE_MIN)
        self.PIXELS_PER_CIE_Y = self.Y_PIXEL_LENGTH / (self.Y_CIE_MAX - self.Y_CIE_MIN)

    def cie_to_pixel(self, cie_x: float, cie_y: float) -> Tuple[float, float]:
        """Converts a single (x, y) CIE coordinate to (x, y) pixel coordinate."""

        # Calculate X pixel: (cie_x - X_CIE_MIN) * PIXELS_PER_CIE_X + X_PIXEL_START_CIE_0_0
        pixel_x = (cie_x - self.X_CIE_MIN) * self.PIXELS_PER_CIE_X + self.X_PIXEL_START_CIE_0_0

        # Calculate Y pixel: It's inverted.
        # Y_PIXEL_END_CIE_0_0 - (cie_y - Y_CIE_MIN) * PIXELS_PER_CIE_Y
        pixel_y = self.Y_PIXEL_END_CIE_0_0 - (cie_y - self.Y_CIE_MIN) * self.PIXELS_PER_CIE_Y

        return round(pixel_x, 2), round(pixel_y, 2)

    def get_triangle_pixel_points(self, cie_coords: List[List[float]]) -> str:
        """
        Converts a list of 3 CIE coordinate pairs [[rx, ry], [gx, gy], [bx, by]]
        into an SVG 'points' string.
        """
        # Updated validation: Check for 3 pairs, each with 2 values
        if (not cie_coords or
                len(cie_coords) != 3 or
                not all(isinstance(p, (list, tuple)) and len(p) == 2 for p in cie_coords)):
            logger.warning(f"Invalid coordinate structure passed to get_triangle_pixel_points: {cie_coords}")
            return ""

        try:
            # Unpack the list of lists
            (r_x, r_y) = cie_coords[0]
            (g_x, g_y) = cie_coords[1]
            (b_x, b_y) = cie_coords[2]

            # Ensure they are floats
            r_x, r_y = float(r_x), float(r_y)
            g_x, g_y = float(g_x), float(g_y)
            b_x, b_y = float(b_x), float(b_y)

            # Convert each pair (this part is unchanged)
            r_px = self.cie_to_pixel(r_x, r_y)
            g_px = self.cie_to_pixel(g_x, g_y)
            b_px = self.cie_to_pixel(b_x, b_y)

            # Format as SVG string "x1,y1 x2,y2 x3,y3"
            return f"{r_px[0]},{r_px[1]} {g_px[0]},{g_px[1]} {b_px[0]},{b_px[1]}"

        except (TypeError, ValueError, IndexError) as e:
            logger.error(f"Error converting triangle points: {e}")
            return ""

    def get_debug_grid_points(self) -> str:
        """
        Generates SVG circles for the 4 corners of the axis for alignment debugging.
        Returns a list of dictionaries for the template.
        """
        points = {
            "bottom_left": self.cie_to_pixel(self.X_CIE_MIN, self.Y_CIE_MIN),
            "bottom_right": self.cie_to_pixel(self.X_CIE_MAX, self.Y_CIE_MIN),
            "top_left": self.cie_to_pixel(self.X_CIE_MIN, self.Y_CIE_MAX),
            "top_right": self.cie_to_pixel(self.X_CIE_MAX, self.Y_CIE_MAX)
        }
        # We'll pass this dict to Jinja and let the template render it.
        # Returning as JSON string for easy embedding.
        return json.dumps(points)