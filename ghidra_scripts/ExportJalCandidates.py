# Ghidra Jython script: export JAL instructions and their outgoing references to CSV.
# Run inside Ghidra after importing/analyzing the ELF with the PS2 Emotion Engine language.
# This is a triage aid, not an automatic patcher.
from java.io import FileWriter, BufferedWriter
from ghidra.util.task import ConsoleTaskMonitor

out_file = askFile("Choose CSV output file", "Save")
listing = currentProgram.getListing()
memory = currentProgram.getMemory()

def csv_cell(value):
    text = str(value).replace('"', '""').replace('\r', ' ').replace('\n', ' ')
    return '"' + text + '"'

writer = BufferedWriter(FileWriter(out_file))
writer.write("address,bytes,mnemonic,operands,flow_targets,target_memory_block,target_executable_block\n")
count = 0
try:
    instructions = listing.getInstructions(True)
    while instructions.hasNext() and not monitor.isCancelled():
        ins = instructions.next()
        mnemonic = ins.getMnemonicString().upper()
        if mnemonic != "JAL":
            continue
        refs = ins.getReferencesFrom()
        targets = []
        for ref in refs:
            if ref.getReferenceType().isCall() or ref.getReferenceType().isJump():
                targets.append(ref.getToAddress())
        if not targets:
            flows = ins.getFlows()
            for target in flows:
                targets.append(target)
        if not targets:
            targets = [""]
        for target in targets:
            block_name = ""
            executable = ""
            if target != "":
                block = memory.getBlock(target)
                if block is not None:
                    block_name = block.getName()
                    executable = str(block.isExecute())
            operands = []
            for i in range(ins.getNumOperands()):
                operands.append(ins.getDefaultOperandRepresentation(i))
            row = [
                ins.getAddress(), ins.getBytes().hex(),
                mnemonic, " ".join(operands), target, block_name, executable
            ]
            writer.write(",".join(csv_cell(x) for x in row) + "\n")
            count += 1
finally:
    writer.close()
print("Exported %d JAL reference row(s) to %s" % (count, out_file.getAbsolutePath()))
print("Review candidates manually; this script does not prove an instruction is invalid.")
