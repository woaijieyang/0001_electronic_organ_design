const path=require('path');const sharp=require('sharp');
const root=path.resolve(__dirname,'..','assets','figures');
(async()=>{for(const name of ['readme-cover','controls','design-journey','tech-stack']){
 await sharp(path.join(root,name+'.svg')).png().toFile(path.join(root,name+'.png'));
 console.log(name);
}})().catch(e=>{console.error(e);process.exit(1)});
