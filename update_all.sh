
for folder in examples/* ; do 
    cd $folder
    copier recopy -A
    cd ../..  
done


