# VHCameraPlotter
Simple TKinter Program for Visualizing Valid SM64 Camera Positions

This program allows the user to read in focal point/yaw ranges and visualize 
the in-bounds camera positions that satisfy those ranges. The valid camera 
positions are shown in white.

Files are expected to be a sequence of lines with the following format:

`fp_x,fp_z` : `yaw_range_1_start,yaw_range_1_end,...,yaw_range_n_start,yaw_range_n_end`
                            
Note the colon separating the focal point entries from the yaw range entries.

Each line needs at least two entries for the focal point, and each valid
yaw range should include a start and end point. This means the total number 
of entries should be even. Furthermore, yaw ranges are assumed to travel
counter-clockwise from the start of the range to the end of the range, or
in the direction of increasing AU. To give some concrete examples of what 
I mean by this:

 - The range 16384 to 32768 will assume the quarter-circle range from +X to -Z
 - The range 49152 to 16284 will assume the half-circle range including +Z, NOT
   the half-circle range including -Z
 - The range 48005 to 48000 will include nearly the entire circle range, NOT the 
   small wedge between 48000 and 48005. 

Note that in the examples above I assume the following convention:
 - +Z is 0
 - +X is 16384
 - -Z is 32768
 - -X is 49152

The generated plot has bounds [-8192,8191] in X and Z, and is scaled down 
by a factor of 16 in each direction for easier generation/viewing. 

In addition, the user can add specific test points, which will be shown as
circles on the plot. Test points within an acceptable region are shown in 
green, and test points outside all acceptable regions are shown in orange.
