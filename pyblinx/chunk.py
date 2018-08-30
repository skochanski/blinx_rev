from node import Node
from struct import unpack
from texlist import Texlist
from address import section_addresses
from address import rawaddress
from helpers import verify_file_arg_o
from helpers import verify_file_arg_b
from world_transform import transform
import operator

class Chunk(Node) :
    section_table = section_addresses()

    def __init__(self, xbe, entry_offset, section, texlist=None, parent_coords=None, full=True) :
        Node.__init__(self, xbe, entry_offset, section, texlist, parent_coords)

        block = self.parse_block()
        self.voffset = rawaddress(block['voffset'], self.section, Chunk.section_table)
        self.toffset = rawaddress(block['toffset'], self.section, Chunk.section_table)

        self.name = 'ch_' + self.section + '_' + hex(self.offset)

        self.vertices = None
        self.triangles = None

        if full is True :
            self.vertices, self.triangles = self.parse(world=True)


    def parse_block(self) :
        '''
        Parse pointer block and return data.
        '''
        f = self.xbe
        offset = rawaddress(self.block, self.section, Chunk.section_table)
        f.seek(offset)
        vdata_offset = unpack('i', f.read(4))[0]
        tdata_offset = unpack('i', f.read(4))[0]

        float_array_0 = []
        for _ in range(6) : float_array_0.append(unpack('f', f.read(4))[0])
        
        return {
            'voffset': vdata_offset,
            'toffset': tdata_offset,
            'farray': float_array_0
        }


    def parse(self, world=True) :
        '''
        Parse vetices and triangles in chunk.
        '''
        v = self.parse_vertices(world=world)
        t = self.parse_triangles()
        return v, t

    def write(self, file, texlist=None, clist=False) :
        '''
        Write .obj to open file handle. If texlist is not None, reference material library.
        '''
        f = verify_file_arg_o(file, usage='w+')
        if texlist is not None and clist is False :
            f.write('mtllib {}.mtl\n'.format(texlist.name))

        f.write('o {}\n'.format(self.name))
        self.write_vertices(f)
        self.write_texcoords(f)
        self.write_triangles(f, texlist.matlist)

    

    def parse_vertices(self, world=True) :
        '''
        Reads vertex list from xbe. Returns a list[count], where each element is a tuple[3] denoting xyz.
        '''
        f = self.xbe
        f.seek(self.voffset + 6)
        count = unpack('h', f.read(2))[0]
        f.seek(8, 1)

        print('Parsing {} vertices at {}... '.format(count, hex(self.voffset)), end='')


        v = []
        for _ in range(count) :
            word = list(unpack('fff', f.read(12)))

            if world is True :
                w = tuple(map(operator.add, self.world_coords, self.parent_coords))
                #print(str(self.world_coords[:3]) + ' + ' + str(self.parent_coords[:3]) + ' = ' + str(w[:3]))
                word = transform(word, w)

            v.append(tuple(word))
            f.seek(4, 1)

        print('Done')

        self.vertices = v
        return v

    def parse_triangles(self) :
        '''
        Read tripart list from xbe. Returns a list of tuples (tripart, texlist index) as defined in parse_tripart() without escape flag
        '''
        f = self.xbe
        f.seek(self.toffset)

        print('Parsing triangles at {}... '.format(hex(self.toffset)))

        # Hacky fix around unknown value at 0xbc58 in MDLEN. Probably others like it.
        if unpack('i', f.read(4))[0] > 50 :
            f.seek(-4, 1)

        # TODO: Research header flavors and usage.
        f.seek(2, 1)
        header_size = unpack('h', f.read(2))[0] * 2
        f.seek(header_size, 1)

        t = []

        i = 0
        while(True) :
            print('\tParsing tripart {}'.format(i))
            i += 1

            tripart = self.parse_tripart()
            if(tripart[0] is not None and tripart[1] is not None) :     #TODO: improve readability
                t.append((tripart[0], tripart[1]))
            if tripart[2] : break
            
        print('Done')
        self.triangles = t
        return t
        
    def parse_tripart(self) :
        '''
        Reads tripart. Returns tuple (tripart, texlist index, last) where tripart is a list of tuples (vertex index, tex_x, tex_y),
        texlist index assigns the texture, and last is the escape flag.
        '''
        f = self.xbe

        t = []
        escape = False
        type_spec = unpack('h', f.read(2))[0]

        # Temporary simple tristrip handling
        if (type_spec - 0x0408) % 0x1000 != 0 :
            print('\tNon-texture tripart detected. Aborting')
            print(hex(type_spec - 0x0408))
            return(None, None, True)   

        texlist_index = unpack('h', f.read(2))[0] ^ 0x4000     
        f.seek(2, 1)
        
        # Check if last tripart 
        # TODO: Handle chunks with multiple triangle data regions
        # TODO: Process SIMPLE tristrips
        tripart_size = unpack('h', f.read(2))[0] * 2
        f.seek(tripart_size, 1) 
        tripart_end = f.tell()
        esc_candidate = f.read(4)
        if esc_candidate is b'\xff\x00\x00\x00' :  escape = True    # Escape symbol
        if unpack('f', esc_candidate)[0] < 1.5 : escape = True      # The first four bytes of tpart headers is a float ~2.0. Hacky. Improve.
        f.seek(-(tripart_size + 4), 1)

        t_length = unpack('h', f.read(2))[0]
        for i in range(t_length) :
            strip = []
            s_length = abs(unpack('h', f.read(2))[0])

            for _ in range(s_length) :
                raw_point = list(unpack('hhh', f.read(6)))
                raw_point[0] += 1               #TODO: clean up
                raw_point[1] /= 255.0
                raw_point[2] /= -255.0
                raw_point[2] += 1.0
                data_point = tuple(raw_point)
                strip.append(data_point)

            t.append(strip)

        f.seek(tripart_end)
        return (t, texlist_index, escape)

    def write_vertices(self, file) :
        f = verify_file_arg_o(file)

        verts = self.vertices
        print('Writing vertices to {}'.format(f.name))
        if not verts :
            print('\tNo vertices found!')
            return None
        
        for v in verts :
            ln = 'v {} {} {}\n'.format(v[0], v[1], v[2])
            f.write(ln)

    def write_triangles(self, file, matlist=None) : 
        f = verify_file_arg_o(file)

        if not self.triangles :
            print('\tNo triangles found!')
            return None

        #TODO: write non-texture materials
        #TODO: implement material writing
        vt = 1
        triangles = self.triangles
        for tp in triangles :
            if matlist is not None :
                ln = 'usemtl {}\n'.format(matlist[tp[1]])
                f.write(ln)

            for ts in tp[0] :
                for c in range(len(ts) - 2) :
                    if c % 2 == 0 : ln = 'f {v0}/{vt0} {v1}/{vt1} {v2}/{vt2}\n'.format(v0=ts[c][0], vt0=vt, v1=ts[c+1][0], vt1=vt+1, v2=ts[c+2][0], vt2=vt+2)
                    else :  ln = 'f {v1}/{vt1} {v0}/{vt0} {v2}/{vt2}\n'.format(v0=ts[c][0], vt0=vt, v1=ts[c+1][0], vt1=vt+1, v2=ts[c+2][0], vt2=vt+2)
                    vt += 1
                    f.write(ln)
                vt += 2

    def write_texcoords(self, file) :
        f = verify_file_arg_o(file)
        triangles = self.triangles

        if not triangles :
            print('\tNo texcoords found!')
            return None

        for tp in triangles :
            for ts in tp[0] :
                for c in ts :
                    vt = list(c[1:])
                    ln = 'vt {u} {v}\n'.format(u=str(vt[0]), v=str(vt[1]))
                    f.write(ln)