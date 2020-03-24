# Hateno examples

The examples listed in this folder (more are coming!) show how Hateno can be used to manager and generate simulations.

The first things to do to use Hateno is to configure the folder where the simulations will be stored. To do that, create a file `.simulations.conf` into it and indicate all informations about the simulations.

The example folder `count` contains such a file, and some others. While `.simulations.conf` is required, the others are not, and are just here to keep the examples organized. The file `count.py` is the program that must be executed to generate the simulations. The files `add.json` and `add-generated.py` show two ways to indicate to Hateno which simulations we want to extract/add/delete/create.

For example, assume that the simulation described in `add.json` exists and is stored into the simulations folder. Than, we can retrieve it by using the manager:

```
hateno-manager examples/count extract examples/count/add.json
```

Now, we want the simulations described in `add-generated.py`. Instead of using the manager, we can use the maker to extract them: if they don't exist, the maker will generate them, based on the informations stored in `maker.json`:

```
hateno-maker --settings examples/maker.json examples/count examples/count/add-generated.py
```
