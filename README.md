# Blinx Rev
Work towards extracting assets and data from Blinx: The Time Sweeper. In its current phase, the goal of the project is to extract 3d assets from the game's binary and store them as .obj files. Information on patterns and format is available in the wiki, which will be updated as research progresses. Requires Python 3.5+.

### Getting Started
The project is currently experimental and requires extremely specific usage to provide meaningful results. This setup is prone to simplify as research is conducted and implemented.

All 3d assets are contained in Blinx's xbe. Use [XBE Explorer](https://sourceforge.net/projects/dxbx/files/XBE%20Explorer/) to find the proper sections. Everything after .data and before DOLBY is potential asset data.

Once you choose a section, look for a chunk that represents a model. Chunks have two parts, a triangle list and a vertex list. All elements of the triangle list are 16-bit ints, while elements of the vertex list are 32-bit floats.

#### Mode
The project has two modes -- chunk=0, vert/tri=1. Currently chunk is not implemented. Use vert/tri and provide vert and tri files.

*Everything under here is outdated. Check on the wiki for the most up to date info*


#### Triangle lists
Triangle lists are lists of 16-bit ints that represent vertex indices in the vertex list. There are multiple types of models. Currently there are two known types -- simple and complex. However, there seems to exist other types. The triangle lists of these types are different.

##### Simple
Simple triangle lists only contain vertex indices. They usually start after value `0xffffff05` or `0xffffff0b` and always terminate with `0xff000000`. They have a 4-byte header, the first 2 bytes are unknown and the second 2 bytes denote the size of the list. The support for this type is depricated, but will be revisited soon.

##### Complex
Complex triangle lists are a list of trilist structures. Trilist structures contain a `size` short an array of points `size` long. A point is a structure containing a vertice index short and two other shorts, probably holding uv data. Each complex model has a 10-byte header after value `0x7f7f7fff`. The project supports complex models, and handles the header.

#### Vertex lists
Vertex lists are the same for all types of models. They have a 20-byte header following the triangle list's `0xff000000`. Then, the vertex data. Each line of vertex data contains 3 valid floats then some unknown 4-byte value. The project __does not__ currently handle the header and must start on the first valid float of the first line. The vertex list terminates with `0xff000000`.

#### Footer
Each model seems to have a footer with unknown data. They usually seem to be 96 bytes in length. After *some* complex models there is a list of 32-byte strings with names of texture files from the Media folder.

### Disclaimer
The development of these tools is purely experimental and educational. All research is conducted on legally-obtained games and with publicly-available information. 
